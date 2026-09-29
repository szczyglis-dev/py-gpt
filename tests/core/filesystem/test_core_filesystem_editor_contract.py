from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.filesystem.editor import Editor


def make_editor(tmp_path):
    dialog = SimpleNamespace(
        file=None,
        base_content="",
        reset_file_title=MagicMock(),
        update_file_title=MagicMock(),
        is_changed=MagicMock(return_value=True),
    )
    widget = SimpleNamespace(
        clear=MagicMock(), on_update=MagicMock(), on_destroy=MagicMock(),
        setPlainText=MagicMock(), toPlainText=MagicMock(return_value="content"),
    )
    path_widget = SimpleNamespace(setText=MagicMock())
    dialogs = SimpleNamespace(alert=MagicMock())
    window = SimpleNamespace(
        ui=SimpleNamespace(dialog={"d": dialog}, editor={"d": widget}, paths={"d": path_widget}, dialogs=dialogs),
        core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())),
        controller=SimpleNamespace(files=SimpleNamespace(update_explorer=MagicMock())),
        update_status=MagicMock(),
    )
    return Editor(window), window, dialog, widget


def test_clear_destroy_and_is_changed(tmp_path):
    editor, window, dialog, widget = make_editor(tmp_path)
    dialog.file = "x.txt"; dialog.base_content = "old"
    editor.clear("d")
    widget.clear.assert_called_once()
    assert dialog.file is None and dialog.base_content == ""
    dialog.reset_file_title.assert_called_once()
    widget.on_update.assert_called_once()
    assert editor.is_changed("d") is True
    editor.destroy("d")
    widget.on_destroy.assert_called_once()


def test_load_existing_and_missing_file(tmp_path):
    editor, window, dialog, widget = make_editor(tmp_path)
    missing = tmp_path / "missing.txt"
    editor.load("d", str(missing))
    window.update_status.assert_called_with(f"File not found: {missing}")

    path = tmp_path / "a.txt"; path.write_text("hello", encoding="utf-8")
    editor.load("d", str(path))
    widget.setPlainText.assert_called_with("hello")
    assert dialog.base_content == "hello"
    dialog.update_file_title.assert_called()


def test_restore_reloads_current_file(tmp_path, monkeypatch):
    editor, window, dialog, _ = make_editor(tmp_path)
    dialog.file = str(tmp_path / "x.txt")
    editor.load = MagicMock()
    editor.restore("d")
    editor.load.assert_called_once_with("d", dialog.file)
    window.update_status.assert_called_with(f"Reloaded file: {dialog.file}")


def test_save_updates_base_content_and_warns_for_invalid_json(tmp_path):
    editor, window, dialog, widget = make_editor(tmp_path)
    widget.toPlainText.return_value = "{bad"
    path = tmp_path / "bad.json"
    editor.save("d", str(path))
    assert path.read_text() == "{bad"
    assert dialog.file == str(path)
    assert dialog.base_content == "{bad"
    window.ui.dialogs.alert.assert_called_once()
    dialog.update_file_title.assert_called_with(force=True)
    window.controller.files.update_explorer.assert_called_once()
