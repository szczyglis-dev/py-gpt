import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.text_editor.tool import TextEditor


def _tool():
    tool = TextEditor()
    filesystem = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(filesystem=filesystem),
        ui=SimpleNamespace(dialogs=MagicMock(), dialog={}, editor={}),
        update_status=MagicMock(),
    )
    tool.window = window
    return tool


def test_text_editor_defaults_setup_and_prepare_id():
    tool = _tool()
    spawner = object()
    with patch("pygpt_net.tools.text_editor.tool.DialogSpawner", return_value=spawner) as cls:
        tool.setup()
    cls.assert_called_once_with(tool.window)
    assert tool.spawner is spawner
    assert tool.id == "editor"
    assert tool.width == 800 and tool.height == 500

    expected = "file_editor_" + hashlib.md5("/tmp/a.txt".encode("utf-8")).hexdigest()
    assert tool.prepare_id("/tmp/a.txt") == expected


def test_text_editor_open_file_confirms_changed_document_before_dialog():
    tool = _tool()
    tool.window.core.filesystem.editor.is_changed.return_value = True
    with patch("pygpt_net.tools.text_editor.tool.trans", return_value="changed"):
        tool.open_file("id")
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="editor.changed.open", id="id", msg="changed")


def test_text_editor_open_file_can_save_then_open_selected_path():
    tool = _tool()
    tool.window.core.filesystem.editor.is_changed.return_value = False
    tool.save = MagicMock()
    tool.open = MagicMock()
    with patch("pygpt_net.tools.text_editor.tool.QFileDialog.getOpenFileName", return_value=("/tmp/x.txt", "")):
        tool.open_file("id", auto_close=False, save=True)
    tool.save.assert_called_once_with("id")
    tool.open.assert_called_once_with("/tmp/x.txt", "id", False)


def test_text_editor_clear_confirmation_save_close_and_force_clear():
    tool = _tool()
    tool.window.core.filesystem.editor.is_changed.return_value = True
    with patch("pygpt_net.tools.text_editor.tool.trans", return_value="changed"):
        tool.clear("id")
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="editor.changed.clear", id="id", msg="changed")

    tool.window.core.filesystem.editor.is_changed.return_value = False
    tool.save = MagicMock(return_value="new-id")
    tool.close = MagicMock()
    tool.clear("id", force=True, save=True)
    tool.save.assert_called_once_with("id")
    tool.close.assert_called_once_with("new-id")
    tool.window.core.filesystem.editor.clear.assert_called_once_with("new-id")


def test_text_editor_new_and_open_batch_delegate_open():
    tool = _tool()
    tool.open = MagicMock()
    tool.new()
    tool.open.assert_called_once_with()
    tool.open.reset_mock()
    tool.open_batch(["a.txt", "b.txt"])
    assert tool.open.call_args_list[0].args == ("a.txt",)
    assert tool.open.call_args_list[0].kwargs == {"auto_close": False, "force": True}
    assert tool.open.call_args_list[1].args == ("b.txt",)


def test_text_editor_open_rejects_non_utf8_or_unreadable_file(tmp_path):
    tool = _tool()
    path = tmp_path / "bad.txt"
    path.write_bytes(b"\xff\xfe")
    tool.open(str(path))
    tool.window.ui.dialogs.alert.assert_called_once()
    assert "Error opening text file" in tool.window.update_status.call_args.args[0]
    tool.window.ui.dialogs.open_instance.assert_not_called()


def test_text_editor_open_existing_file_loads_and_titles_without_host_dependencies(tmp_path):
    tool = _tool()
    path = tmp_path / "note.txt"
    path.write_text("hello", encoding="utf-8")
    editor_id = tool.prepare_id(str(path))
    dialog = MagicMock(); tool.window.ui.dialog[editor_id] = dialog
    editor = MagicMock(); tool.window.ui.editor[editor_id] = editor
    tool.window.core.filesystem.sizeof_fmt.return_value = "5 B"

    tool.open(str(path))

    tool.window.ui.dialogs.open_instance.assert_called_once_with(editor_id, width=800, height=500)
    assert dialog.file == str(path)
    tool.window.core.filesystem.editor.load.assert_called_once_with(editor_id, str(path))
    dialog.setWindowTitle.assert_called_once_with("note.txt - 5 B")
    editor.setFocus.assert_called_once_with()
    tool.window.update_status.assert_called_once_with("Loaded file: note.txt")


def test_text_editor_open_closes_different_current_editor_and_skips_status_when_forced(tmp_path):
    tool = _tool()
    path = tmp_path / "next.txt"; path.write_text("x", encoding="utf-8")
    editor_id = tool.prepare_id(str(path))
    tool.window.ui.dialog[editor_id] = MagicMock()
    tool.window.ui.editor[editor_id] = MagicMock()
    tool.window.core.filesystem.sizeof_fmt.return_value = "1 B"
    tool.close = MagicMock()

    tool.open(str(path), current_id="old", auto_close=True, force=True)
    tool.close.assert_called_once_with("old")
    tool.window.update_status.assert_not_called()


def test_text_editor_open_new_instance_generates_monotonic_ids_and_clears():
    tool = _tool()
    tool.open(); tool.open()
    assert tool.window.ui.dialogs.open_instance.call_args_list[0].args[0] == "file_tmp_editor_0"
    assert tool.window.ui.dialogs.open_instance.call_args_list[1].args[0] == "file_tmp_editor_1"
    assert tool.instance_id == 2
    assert tool.window.core.filesystem.editor.clear.call_args_list[0].args == ("file_tmp_editor_0",)


def test_text_editor_close_can_save_then_destroy_and_close():
    tool = _tool()
    dialog = MagicMock(); tool.window.ui.dialog["id"] = dialog
    tool.save = MagicMock(return_value="saved-id")
    tool.window.ui.dialog["saved-id"] = dialog

    tool.close("id", save=True)

    tool.save.assert_called_once_with("id")
    assert dialog.accept_close is True
    tool.window.core.filesystem.editor.destroy.assert_called_once_with("saved-id")
    tool.window.ui.dialogs.close.assert_called_once_with("saved-id")


def test_text_editor_save_existing_or_save_as_and_optional_close():
    tool = _tool()
    dialog = MagicMock(); dialog.file = "/tmp/a.txt"
    tool.window.ui.dialog["id"] = dialog
    tool.close = MagicMock()
    assert tool.save("id", close=True) == "id"
    tool.window.core.filesystem.editor.save.assert_called_once_with("id")
    tool.close.assert_called_once_with("id")

    dialog.file = None
    tool.save_as_file = MagicMock(return_value="new-id")
    assert tool.save("id") == "new-id"
    tool.save_as_file.assert_called_once_with("id")


def test_text_editor_restore_confirmation_file_and_no_file_paths():
    tool = _tool()
    dialog = MagicMock(); tool.window.ui.dialog["id"] = dialog
    tool.window.core.filesystem.editor.is_changed.return_value = True
    with patch("pygpt_net.tools.text_editor.tool.trans", return_value="changed"):
        tool.restore("id")
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="editor.changed.restore", id="id", msg="changed")

    tool.window.core.filesystem.editor.is_changed.return_value = False
    dialog.file = "/tmp/a.txt"
    tool.restore("id", force=True)
    tool.window.core.filesystem.editor.restore.assert_called_once_with("id")

    dialog.file = None
    tool.restore("id", force=True)
    tool.window.ui.dialogs.alert.assert_called_with("No file to restore")


def test_text_editor_restore_can_save_before_restoring():
    tool = _tool()
    dialog = MagicMock(); dialog.file = "/tmp/a.txt"; tool.window.ui.dialog["id"] = dialog
    tool.window.core.filesystem.editor.is_changed.return_value = False
    tool.save = MagicMock()
    tool.restore("id", force=True, save=True)
    tool.save.assert_called_once_with("id")
    tool.window.core.filesystem.editor.restore.assert_called_once_with("id")


def test_text_editor_save_as_file_uses_current_basename_and_delegates_save():
    tool = _tool()
    dialog = MagicMock(); dialog.file = "/old/note.txt"; tool.window.ui.dialog["id"] = dialog
    with patch("pygpt_net.tools.text_editor.tool.QFileDialog.getSaveFileName", return_value=("/new/note.txt", "")) as picker, \
            patch("pygpt_net.tools.text_editor.tool.trans", return_value="Save as"):
        result = tool.save_as_file("id")
    assert result == "id"
    assert picker.call_args.args[2] == "note.txt"
    tool.window.core.filesystem.editor.save.assert_called_once_with("id", "/new/note.txt")


def test_text_editor_get_instance_and_lang_mappings():
    tool = _tool()
    tool.spawner = MagicMock(); instance = object(); tool.spawner.setup.return_value = instance
    assert tool.get_instance("text_editor", "id") is instance
    tool.spawner.setup.assert_called_once_with("id")
    assert tool.get_instance("other", "id") is None
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.text.editor": "menu.tools.text.editor"}
    }
