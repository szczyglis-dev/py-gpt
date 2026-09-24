from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

from pygpt_net.ui.dialog.changelog import Changelog


def _window(app_updated=True):
    config = SimpleNamespace(
        get_app_path=MagicMock(return_value="/app"),
        get=MagicMock(side_effect=lambda key, default=None: app_updated if key == "app_updated" else default),
    )
    return SimpleNamespace(
        core=SimpleNamespace(config=config),
        meta={"version": "2.8.30"},
        ui=SimpleNamespace(nodes={}, dialog={}),
    )


def _trans(key):
    if key == "dialog.changelog.updated":
        return "PyGPT has been updated to version: {version}"
    return key


def test_setup_loads_changelog_and_builds_info_dialog():
    window = _window(app_updated=True)
    textarea = MagicMock()
    title_label = MagicMock()
    updated_label = MagicMock()
    dialog = MagicMock()
    layout = MagicMock()

    with patch("builtins.open", mock_open(read_data="Changes")) as opened, \
         patch("pygpt_net.ui.dialog.changelog.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.changelog.QLabel", side_effect=[title_label, updated_label]), \
         patch("pygpt_net.ui.dialog.changelog.QVBoxLayout", return_value=layout), \
         patch("pygpt_net.ui.dialog.changelog.InfoDialog", return_value=dialog), \
         patch("pygpt_net.ui.dialog.changelog.trans", side_effect=_trans):
        Changelog(window).setup()

    opened.assert_called_once_with("/app/CHANGELOG.txt", "r", encoding="utf-8")
    textarea.setPlainText.assert_called_once_with("Changes")
    assert window.ui.nodes["dialog.changelog.label"] is title_label
    assert window.ui.nodes["dialog.changelog.updated"] is updated_label
    updated_label.setAlignment.assert_called_once()
    updated_label.setWordWrap.assert_called_once_with(True)
    updated_label.setVisible.assert_called_once_with(True)
    assert window.ui.dialog["info.changelog"] is dialog
    dialog.setWindowTitle.assert_called_once_with("dialog.changelog.title")


def test_setup_hides_updated_label_when_not_after_update():
    window = _window(app_updated=False)
    updated_label = MagicMock()
    with patch("builtins.open", mock_open(read_data="Changes")), \
         patch("pygpt_net.ui.dialog.changelog.QPlainTextEdit", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.QLabel", side_effect=[MagicMock(), updated_label]), \
         patch("pygpt_net.ui.dialog.changelog.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.InfoDialog", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.trans", side_effect=_trans):
        Changelog(window).setup()

    updated_label.setVisible.assert_called_once_with(False)


def test_setup_survives_missing_changelog():
    window = _window()
    textarea = MagicMock()
    with patch("builtins.open", side_effect=OSError("missing")), \
         patch("pygpt_net.ui.dialog.changelog.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.changelog.QLabel", side_effect=[MagicMock(), MagicMock()]), \
         patch("pygpt_net.ui.dialog.changelog.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.InfoDialog", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.changelog.trans", side_effect=_trans), \
         patch("builtins.print"):
        Changelog(window).setup()
    textarea.setPlainText.assert_called_once_with("")
