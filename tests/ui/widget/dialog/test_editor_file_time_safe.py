from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.dialog.editor_file import EditorFileDialog


def _widget(tmp_path, changed=True, existing=True):
    path = tmp_path / "note.txt"
    if existing:
        path.write_bytes(b"12345")
    window = SimpleNamespace(
        core=SimpleNamespace(filesystem=SimpleNamespace(sizeof_fmt=MagicMock(return_value="5 B"))),
        ui=SimpleNamespace(editor={"editor-x": SimpleNamespace(toPlainText=MagicMock(return_value="changed" if changed else "base"))}),
    )
    return SimpleNamespace(
        file=str(path),
        base_content="base",
        window=window,
        id="editor-x",
        setWindowTitle=MagicMock(),
        is_changed=MagicMock(return_value=changed),
    )


def test_editor_file_title_uses_mocked_clock_not_host_timezone(tmp_path):
    widget = _widget(tmp_path, changed=True, existing=True)
    fixed = datetime(2026, 9, 7, 2, 5)

    with patch("pygpt_net.ui.widget.dialog.editor_file.datetime.datetime") as dt_cls:
        dt_cls.now.return_value = fixed
        EditorFileDialog.update_file_title(widget)

    widget.setWindowTitle.assert_called_once_with("note.txt* - 5 B (02:05)")
    dt_cls.now.assert_called_once_with()


def test_editor_file_title_without_change_or_force_has_no_clock_suffix(tmp_path):
    widget = _widget(tmp_path, changed=False, existing=True)
    with patch("pygpt_net.ui.widget.dialog.editor_file.datetime.datetime") as dt_cls:
        EditorFileDialog.update_file_title(widget, force=False)
    widget.setWindowTitle.assert_called_once_with("note.txt - 5 B")
    dt_cls.now.assert_not_called()


def test_editor_file_is_changed_compares_editor_content_with_base_content():
    editor = SimpleNamespace(toPlainText=MagicMock(return_value="same"))
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(editor={"id": editor})), id="id", base_content="same")
    assert EditorFileDialog.is_changed(widget) is False
    editor.toPlainText.return_value = "different"
    assert EditorFileDialog.is_changed(widget) is True


def test_editor_file_cleanup_closes_settings_only_for_main_editor_dialog():
    settings = SimpleNamespace(active={"editor": True})
    controller = SimpleNamespace(settings=SimpleNamespace(close=MagicMock(), update=MagicMock()))
    widget = SimpleNamespace(id="editor_file", window=SimpleNamespace(core=SimpleNamespace(settings=settings), controller=controller))
    EditorFileDialog.cleanup(widget)
    assert settings.active["editor"] is False
    controller.settings.close.assert_called_once_with("editor")
    controller.settings.update.assert_called_once_with()

    controller.settings.close.reset_mock(); controller.settings.update.reset_mock(); widget.id = "tool-editor"
    EditorFileDialog.cleanup(widget)
    controller.settings.close.assert_not_called()
    controller.settings.update.assert_not_called()
