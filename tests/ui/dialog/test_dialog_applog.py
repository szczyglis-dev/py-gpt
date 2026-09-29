from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

from pygpt_net.ui.dialog.applog import AppLog


def _window(tmp_path=None):
    user_path = str(tmp_path) if tmp_path else "/user"
    editor = MagicMock()
    return SimpleNamespace(
        core=SimpleNamespace(
            config=SimpleNamespace(get_user_path=MagicMock(return_value=user_path)),
            debug=SimpleNamespace(get_log_level_name=MagicMock(return_value="debug")),
        ),
        ui=SimpleNamespace(
            editor={"app.log": editor}, nodes={}, paths={}, dialog={}, dialogs=SimpleNamespace(confirm=MagicMock())
        ),
        controller=SimpleNamespace(files=SimpleNamespace(open=MagicMock())),
    )


def test_get_log_path_uses_user_directory(tmp_path):
    window = _window(tmp_path)
    assert AppLog(window).get_log_path() == str(tmp_path / "app.log")


def test_update_log_level_uppercases_name():
    window = _window()
    label = MagicMock()
    window.ui.nodes["dialog.app.log.level"] = label
    AppLog(window).update_log_level()
    label.setText.assert_called_once_with("Log level: DEBUG")


def test_update_refreshes_path_level_and_reloads_without_showing():
    window = _window()
    label = MagicMock()
    window.ui.nodes["dialog.app.log.label"] = label
    app = AppLog(window)
    with patch.object(app, "get_log_path", return_value="/x/app.log"), \
         patch.object(app, "update_log_level") as level, \
         patch.object(app, "reload") as reload_:
        app.update()
    label.setText.assert_called_once_with("/x/app.log")
    level.assert_called_once()
    reload_.assert_called_once_with(show=False)


def test_reload_reads_utf8_ignoring_invalid_bytes_and_scrolls_to_end(tmp_path):
    path = tmp_path / "app.log"
    path.write_bytes(b"hello\xffworld")
    window = _window(tmp_path)
    dialog = MagicMock(); window.ui.dialog["app.log"] = dialog
    cursor = MagicMock(); window.ui.editor["app.log"].textCursor.return_value = cursor
    with patch("pygpt_net.ui.dialog.applog.QTextCursor", SimpleNamespace(End="END")):
        AppLog(window).reload(show=True)
    window.ui.editor["app.log"].setPlainText.assert_called_once_with("helloworld")
    dialog.show.assert_called_once()
    cursor.movePosition.assert_called_once_with("END")
    window.ui.editor["app.log"].setTextCursor.assert_called_once_with(cursor)


def test_clear_requires_confirmation_unless_forced(tmp_path):
    path = tmp_path / "app.log"
    path.write_text("data", encoding="utf-8")
    window = _window(tmp_path)
    app = AppLog(window)
    with patch.object(app, "reload") as reload_:
        app.clear(force=False)
        assert path.read_text(encoding="utf-8") == "data"
        window.ui.dialogs.confirm.assert_called_once_with(type="app.log.clear", id=-1, msg="Clear app.log file?")
        reload_.assert_not_called()

        app.clear(force=True)
        assert path.read_text(encoding="utf-8") == ""
        reload_.assert_called_once()


def test_open_external_opens_existing_file_only(tmp_path):
    window = _window(tmp_path)
    app = AppLog(window)
    path = tmp_path / "app.log"
    path.write_text("x", encoding="utf-8")
    app.open_external()
    window.controller.files.open.assert_called_once_with(str(path))

    path.unlink()
    window.controller.files.open.reset_mock()
    with patch("builtins.print") as printed:
        app.open_external()
    window.controller.files.open.assert_not_called()
    printed.assert_called_once_with("Log file not found!")
