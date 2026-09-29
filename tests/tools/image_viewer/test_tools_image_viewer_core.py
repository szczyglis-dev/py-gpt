import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.image_viewer.tool import ImageViewer


def _dialog(path=None):
    dlg = MagicMock()
    dlg.path = path
    dlg.width.return_value = 640
    dlg.height.return_value = 400
    dlg.isVisible.return_value = False
    dlg.source = MagicMock(); dlg.source.path = path
    dlg.pixmap = MagicMock(); dlg.pixmap.path = path
    dlg.actions = {
        "tb_prev": MagicMock(), "tb_next": MagicMock(), "tb_open_dir": MagicMock(),
        "tb_save_as": MagicMock(), "tb_copy": MagicMock(), "tb_fullscreen": MagicMock(),
    }
    return dlg


def _tool():
    tool = ImageViewer()
    filesystem = MagicMock(); filesystem.sizeof_fmt.return_value = "10 KB"
    window = SimpleNamespace(
        core=SimpleNamespace(filesystem=filesystem, debug=MagicMock()),
        controller=SimpleNamespace(files=MagicMock()),
        ui=SimpleNamespace(dialogs=MagicMock(), dialog={}, nodes={"dialog.image.pixmap": [MagicMock() for _ in range(4)]}),
        update_status=MagicMock(),
    )
    tool.window = window
    return tool


def test_image_viewer_defaults_setup_prepare_id_and_new():
    tool = _tool()
    spawner = object()
    with patch("pygpt_net.tools.image_viewer.tool.DialogSpawner", return_value=spawner) as cls:
        tool.setup()
    cls.assert_called_once_with(tool.window)
    assert tool.spawner is spawner
    expected = "image_viewer_" + hashlib.md5("/tmp/a.png".encode()).hexdigest()
    assert tool.prepare_id("/tmp/a.png") == expected

    tool.open_preview = MagicMock()
    tool.new()
    tool.open_preview.assert_called_once_with()


def test_image_viewer_open_file_and_batch_delegate_preview():
    tool = _tool(); tool.open_preview = MagicMock()
    with patch("pygpt_net.tools.image_viewer.tool.QFileDialog.getOpenFileName", return_value=("/tmp/a.png", "")):
        tool.open_file("current", auto_close=False)
    tool.open_preview.assert_called_once_with("/tmp/a.png", "current", False)

    tool.open_preview.reset_mock()
    tool.open_preview_batch(["a.png", "b.png"], "id", auto_close=False)
    assert tool.open_preview.call_args_list[0].args == ("a.png", "id", False)
    assert tool.open_preview.call_args_list[1].args == ("b.png", "id", False)


def test_image_viewer_open_preview_standard_existing_dialog(tmp_path):
    tool = _tool()
    path = tmp_path / "b.png"; path.write_bytes(b"img")
    dialog_id = tool.prepare_id(str(path))
    dlg = _dialog()
    tool.window.ui.dialog[dialog_id] = dlg
    tool._list_images_in_dir = MagicMock(return_value=[str(path)])
    tool._update_toolbar_actions_state = MagicMock()
    pixmap = MagicMock(); pixmap.width.return_value = 100; pixmap.height.return_value = 50; pixmap.size.return_value = "size"

    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QPixmap", return_value=pixmap):
        tool.open_preview(str(path))

    dlg.source.setPixmap.assert_called_once_with(pixmap)
    assert dlg.source.path == str(path)
    assert dlg.pixmap.path == str(path)
    assert dlg.path == str(path)
    dlg.setWindowTitle.assert_called_once_with("b.png (100x50px) - 10 KB")
    dlg.set_status_meta.assert_called_once_with(index=1, total=1, img_size="size", file_size_str="10 KB")
    dlg.show.assert_called_once_with()
    assert dlg.resize.call_count == 2
    tool._update_toolbar_actions_state.assert_called_once_with(dialog_id)


def test_image_viewer_open_preview_closes_different_current_id(tmp_path):
    tool = _tool()
    path = tmp_path / "a.png"; path.write_bytes(b"x")
    dialog_id = tool.prepare_id(str(path)); tool.window.ui.dialog[dialog_id] = _dialog()
    tool.close_preview = MagicMock(); tool._list_images_in_dir = MagicMock(return_value=[]); tool._update_toolbar_actions_state = MagicMock()
    pixmap = MagicMock(); pixmap.width.return_value = 1; pixmap.height.return_value = 1; pixmap.size.return_value = MagicMock()
    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QPixmap", return_value=pixmap):
        tool.open_preview(str(path), current_id="old", auto_close=True)
    tool.close_preview.assert_called_once_with("old")


def test_image_viewer_open_preview_blank_creates_dialog_and_empty_state():
    tool = _tool(); created = _dialog()

    def create(dialog_id, **kwargs):
        tool.window.ui.dialog[dialog_id] = created

    tool.window.ui.dialogs.open_instance.side_effect = create
    tool._update_toolbar_actions_state = MagicMock()
    blank = MagicMock(); blank.size.return_value = "empty-size"
    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QPixmap", return_value=blank) as pixmap_cls:
        tool.open_preview()
    pixmap_cls.assert_called_once_with(0, 0)
    created.source.setPixmap.assert_called_once_with(blank)
    assert created.source.path is None and created.pixmap.path is None and created.path is None
    created.setWindowTitle.assert_called_once_with("Image Viewer")
    created.set_status_meta.assert_called_once_with(index=0, total=0, img_size="empty-size", file_size_str="")
    assert tool.instance_id == 1


def test_image_viewer_open_preview_reuse_updates_in_place_without_window_resize(tmp_path):
    tool = _tool(); path = tmp_path / "a.png"; path.write_bytes(b"x")
    dlg = _dialog(str(path)); tool.window.ui.dialog["reuse"] = dlg
    dlg.scroll_area = MagicMock(); dlg._viewport_size.return_value = "target"; dlg._compute_fit_factor.return_value = 0.5
    tool._list_images_in_dir = MagicMock(return_value=[str(path), str(tmp_path / "b.png")])
    tool._update_toolbar_actions_state = MagicMock()
    scaled = object(); pixmap = MagicMock(); pixmap.width.return_value = 20; pixmap.height.return_value = 10
    pixmap.size.return_value = "source-size"; pixmap.scaled.return_value = scaled; pixmap.cacheKey.return_value = 99

    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QPixmap", return_value=pixmap):
        tool.open_preview(str(path), current_id="reuse", auto_close=False, reuse=True)

    dlg.pixmap.setPixmap.assert_called_once_with(scaled)
    assert dlg._zoom_mode == "fit" and dlg._drag_active is False
    assert dlg._fit_factor == 0.5 and dlg._last_src_key == 99 and dlg._last_target_size == "target"
    assert dlg.path == str(path)
    dlg.resize.assert_not_called()


def test_image_viewer_close_preview_and_multi_image_window():
    tool = _tool(); dlg = _dialog(); tool.window.ui.dialog["id"] = dlg
    tool.close_preview("id")
    dlg.resize.assert_called_once_with(639, 399)
    dlg.close.assert_called_once_with()

    image_dialog = MagicMock()
    tool.window.ui.dialog["image"] = image_dialog
    pixmaps = [MagicMock() for _ in range(2)]
    for p in pixmaps:
        p.scaled.return_value = p
    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QPixmap", side_effect=pixmaps):
        tool.open_images(["a.png", "b.png"])
    assert tool.window.ui.nodes["dialog.image.pixmap"][0].path == "a.png"
    assert tool.window.ui.nodes["dialog.image.pixmap"][1].path == "b.png"
    tool.window.ui.nodes["dialog.image.pixmap"][2].setVisible.assert_called_with(False)

    tool.close_images()
    image_dialog.close.assert_called_once_with()


def test_image_viewer_open_and_open_dir_only_for_existing_path():
    tool = _tool()
    with patch("pygpt_net.tools.image_viewer.tool.os.path.exists", side_effect=[True, False, True, False]):
        tool.open("yes.png"); tool.open("no.png")
        tool.open_dir("yes.png"); tool.open_dir("no.png")
    tool.window.controller.files.open.assert_called_once_with("yes.png")
    tool.window.controller.files.open_dir.assert_called_once_with("yes.png", True)


def test_image_viewer_save_by_id_and_save_none_status():
    tool = _tool(); tool.save = MagicMock(); tool.window.ui.dialog["id"] = SimpleNamespace(path="a.png")
    tool.save_by_id("id"); tool.save.assert_called_once_with("a.png")
    tool.window.ui.dialog["empty"] = SimpleNamespace(path=None)
    tool.save_by_id("empty")
    tool.window.update_status.assert_called_with("No image to save")

    tool.save = ImageViewer.save.__get__(tool, ImageViewer)
    tool.save(None)
    tool.window.update_status.assert_called_with("No image to save")


def test_image_viewer_save_copies_selected_path_and_logs_failures():
    tool = _tool()
    with patch("pygpt_net.tools.image_viewer.tool.QFileDialog.getSaveFileName", return_value=("/dst/a.png", "")), \
            patch("pygpt_net.tools.image_viewer.tool.shutil.copyfile") as copyfile, \
            patch("pygpt_net.tools.image_viewer.tool.trans", side_effect=lambda key: key):
        tool.save("/src/a.png")
    copyfile.assert_called_once_with("/src/a.png", "/dst/a.png")
    tool.window.update_status.assert_called_with("status.img.saved: a.png")

    with patch("pygpt_net.tools.image_viewer.tool.QFileDialog.getSaveFileName", return_value=("/dst/a.png", "")), \
            patch("pygpt_net.tools.image_viewer.tool.shutil.copyfile", side_effect=OSError("no")):
        tool.save("/src/a.png")
    tool.window.core.debug.log.assert_called_once()


def test_image_viewer_delete_confirmation_force_and_errors():
    tool = _tool()
    tool.delete(None)
    tool.window.update_status.assert_called_with("No image to delete")

    with patch("pygpt_net.tools.image_viewer.tool.trans", return_value="confirm"):
        tool.delete("/tmp/a.png")
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="img_delete", id="/tmp/a.png", msg="confirm")

    tool.window.ui.nodes["dialog.image.pixmap"][1].path = "/tmp/a.png"
    with patch("pygpt_net.tools.image_viewer.tool.os.remove") as remove:
        tool.delete("/tmp/a.png", force=True)
    remove.assert_called_once_with("/tmp/a.png")
    tool.window.ui.nodes["dialog.image.pixmap"][1].setVisible.assert_called_once_with(False)


def test_image_viewer_prev_next_open_dir_actions_and_missing_states():
    tool = _tool(); dlg = _dialog("/d/b.png"); tool.window.ui.dialog["id"] = dlg
    tool._get_neighbors = MagicMock(return_value=("/d/a.png", "/d/c.png")); tool.open_preview = MagicMock(); tool.open_dir = MagicMock()
    tool.prev_by_id("id"); tool.next_by_id("id"); tool.open_dir_by_id("id")
    assert tool.open_preview.call_args_list[0].args == ("/d/a.png",)
    assert tool.open_preview.call_args_list[0].kwargs == {"current_id": "id", "auto_close": False, "reuse": True}
    assert tool.open_preview.call_args_list[1].args == ("/d/c.png",)
    tool.open_dir.assert_called_once_with("/d/b.png")

    tool.window.ui.dialog.clear()
    tool.prev_by_id("id"); tool.next_by_id("id"); tool.open_dir_by_id("id")
    messages = [c.args[0] for c in tool.window.update_status.call_args_list[-3:]]
    assert messages == ["No image selected", "No image selected", "No image to open in directory"]


def test_image_viewer_copy_prefers_existing_source_pixmap():
    tool = _tool(); dlg = _dialog("/d/a.png"); tool.window.ui.dialog["id"] = dlg
    pixmap = MagicMock(); pixmap.isNull.return_value = False
    dlg.source.pixmap.return_value = pixmap
    clipboard = MagicMock()
    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QGuiApplication.clipboard", return_value=clipboard):
        tool.copy_by_id("id")
    clipboard.setPixmap.assert_called_once_with(pixmap)
    tool.window.update_status.assert_called_with("Image copied to clipboard")


def test_image_viewer_copy_missing_or_null_reports_status():
    tool = _tool(); tool.copy_by_id("missing")
    tool.window.update_status.assert_called_with("No dialog")

    dlg = _dialog(None); dlg.source.pixmap.return_value = None; tool.window.ui.dialog["id"] = dlg
    tool.copy_by_id("id")
    tool.window.update_status.assert_called_with("No image to copy")


def test_image_viewer_fullscreen_geometry_toggle_and_primary_screen_fallback():
    tool = _tool(); dlg = _dialog("a.png"); tool.window.ui.dialog["id"] = dlg
    dlg._edge_max = False; dlg.geometry.return_value = "normal"; dlg.windowHandle.return_value = None
    screen = MagicMock(); screen.availableGeometry.return_value = "available"
    with patch("pygpt_net.tools.image_viewer.tool.QtGui.QGuiApplication.screenAt", return_value=None), \
            patch("pygpt_net.tools.image_viewer.tool.QtGui.QGuiApplication.primaryScreen", return_value=screen):
        tool.toggle_fullscreen_by_id("id")
    assert dlg._edge_normal_geom == "normal" and dlg._edge_max is True
    dlg.setGeometry.assert_called_once_with("available")

    dlg.setGeometry.reset_mock(); dlg._edge_max = True; dlg._edge_normal_geom = "normal"
    tool.toggle_fullscreen_by_id("id")
    dlg.showNormal.assert_called()
    dlg.setGeometry.assert_called_once_with("normal")
    assert dlg._edge_max is False


def test_image_viewer_directory_helpers_are_case_insensitive_sorted_and_wrap(tmp_path):
    tool = _tool()
    (tmp_path / "B.JPG").write_bytes(b"")
    (tmp_path / "a.png").write_bytes(b"")
    (tmp_path / "c.webp").write_bytes(b"")
    (tmp_path / "ignore.txt").write_text("x")

    files = tool._list_images_in_dir(str(tmp_path / "a.png"))
    assert [p.split("/")[-1] for p in files] == ["a.png", "B.JPG", "c.webp"]
    prev_path, next_path = tool._get_neighbors(str(tmp_path / "a.png"))
    assert prev_path.endswith("c.webp") and next_path.endswith("B.JPG")
    assert tool._has_multiple_in_dir(str(tmp_path / "a.png")) is True
    assert tool._has_multiple_in_dir(None) is False
    assert ".webp" in tool._image_exts()


def test_image_viewer_neighbors_case_insensitive_and_single_or_missing():
    tool = _tool()
    tool._list_images_in_dir = MagicMock(return_value=["/d/A.PNG", "/d/B.PNG"])
    assert tool._get_neighbors("/d/a.png") == ("/d/B.PNG", "/d/B.PNG")
    assert tool._get_neighbors("/d/missing.png") == (None, None)
    tool._list_images_in_dir.return_value = ["/d/A.PNG"]
    assert tool._get_neighbors("/d/A.PNG") == (None, None)


def test_image_viewer_list_images_logs_os_errors():
    tool = _tool()
    with patch("pygpt_net.tools.image_viewer.tool.os.path.isdir", return_value=True), \
            patch("pygpt_net.tools.image_viewer.tool.os.listdir", side_effect=OSError("bad")):
        assert tool._list_images_in_dir("/d/a.png") == []
    tool.window.core.debug.log.assert_called_once()


def test_image_viewer_toolbar_actions_state_tracks_image_and_neighbors():
    tool = _tool(); dlg = _dialog("/d/a.png"); tool.window.ui.dialog["id"] = dlg
    tool._has_multiple_in_dir = MagicMock(return_value=True)
    tool._update_toolbar_actions_state("id")
    dlg.actions["tb_prev"].setEnabled.assert_called_once_with(True)
    dlg.actions["tb_next"].setEnabled.assert_called_once_with(True)
    for name in ("tb_open_dir", "tb_save_as", "tb_copy", "tb_fullscreen"):
        dlg.actions[name].setEnabled.assert_called_once_with(True)

    dlg.path = None
    tool._update_toolbar_actions_state("id")
    dlg.actions["tb_prev"].setEnabled.assert_called_with(False)
    dlg.actions["tb_copy"].setEnabled.assert_called_with(False)


def test_image_viewer_get_instance_and_lang_mappings():
    tool = _tool(); tool.spawner = MagicMock(); instance = object(); tool.spawner.setup.return_value = instance
    assert tool.get_instance("image_viewer", "id") is instance
    tool.spawner.setup.assert_called_once_with("id")
    assert tool.get_instance("other", "id") is None
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.image.viewer": "menu.tools.image.viewer"}
    }
