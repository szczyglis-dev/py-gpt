from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.logger import Logger


def _window(with_commands=True):
    if with_commands:
        console = SimpleNamespace(get_supported_commands=MagicMock(return_value=["help", "clear"]), on_send=MagicMock())
    else:
        console = SimpleNamespace(on_send=MagicMock())
    debug = SimpleNamespace(console=console)
    return SimpleNamespace(
        core=SimpleNamespace(debug=debug),
        controller=SimpleNamespace(debug=SimpleNamespace(clear_logger=MagicMock())),
        ui=SimpleNamespace(nodes={}, dialog={}),
    )


def test_setup_configures_editor_console_commands_and_dialog():
    window = _window()
    editor = MagicMock(); console_input = MagicMock(); dialog = MagicMock(); send = MagicMock(); clear = MagicMock()
    with patch("pygpt_net.ui.dialog.logger.CodeEditor", return_value=editor), \
         patch("pygpt_net.ui.dialog.logger.ConsoleInput", return_value=console_input), \
         patch("pygpt_net.ui.dialog.logger.QPushButton", side_effect=[send, clear]), \
         patch("pygpt_net.ui.dialog.logger.QHBoxLayout", side_effect=[MagicMock(), MagicMock()]), \
         patch("pygpt_net.ui.dialog.logger.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.LoggerDialog", return_value=dialog), \
         patch("pygpt_net.ui.dialog.logger.trans", side_effect=lambda key: key):
        Logger(window).setup()

    assert window.logger is editor
    assert window.console is console_input
    editor.setReadOnly.assert_called_once_with(True)
    editor.setProperty.assert_called_once_with("class", "text-editor")
    console_input.set_commands.assert_called_once_with(["help", "clear"])
    send.clicked.connect.assert_called_once_with(window.core.debug.console.on_send)
    assert window.ui.nodes["logger.btn.clear"] is clear
    assert window.ui.dialog["logger"] is dialog
    dialog.setWindowTitle.assert_called_once_with("dialog.logger.title")
    dialog.resize.assert_called_once_with(800, 500)


def test_setup_does_not_request_commands_when_console_is_unavailable():
    window = _window(with_commands=False)
    console_input = MagicMock()
    with patch("pygpt_net.ui.dialog.logger.CodeEditor", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.ConsoleInput", return_value=console_input), \
         patch("pygpt_net.ui.dialog.logger.QPushButton", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.QHBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.LoggerDialog", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.logger.trans", side_effect=lambda key: key):
        Logger(window).setup()
    console_input.set_commands.assert_not_called()
