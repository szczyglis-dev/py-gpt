from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

from pygpt_net.ui.dialog.changelog import Changelog


def _window():
    return SimpleNamespace(
        core=SimpleNamespace(config=SimpleNamespace(get_app_path=MagicMock(return_value="/app"))),
        ui=SimpleNamespace(nodes={}, dialog={}),
    )


def test_setup_loads_changelog_and_builds_info_dialog():
    window = _window()
    textarea = MagicMock()
    label = MagicMock()
    dialog = MagicMock()
    with patch("builtins.open", mock_open(read_data="Changes")) as opened, \
         patch("pygpt_net.ui.dialog.changelog.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.changelog.QLabel", return_value=label), \
         patch("pygpt_net.ui.dialog.changelog.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.InfoDialog", return_value=dialog), \
         patch("pygpt_net.ui.dialog.changelog.trans", side_effect=lambda key: key):
        Changelog(window).setup()
    opened.assert_called_once_with("/app/CHANGELOG.txt", "r", encoding="utf-8")
    textarea.setPlainText.assert_called_once_with("Changes")
    assert window.ui.nodes["dialog.changelog.label"] is label
    assert window.ui.dialog["info.changelog"] is dialog
    dialog.setWindowTitle.assert_called_once_with("dialog.changelog.title")


def test_setup_survives_missing_changelog():
    window = _window()
    textarea = MagicMock()
    with patch("builtins.open", side_effect=OSError("missing")), \
         patch("pygpt_net.ui.dialog.changelog.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.changelog.QLabel", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.InfoDialog", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.trans", side_effect=lambda key: key), \
         patch("builtins.print"):
        Changelog(window).setup()
    textarea.setPlainText.assert_called_once_with("")
