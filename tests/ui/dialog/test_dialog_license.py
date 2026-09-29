from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, call, mock_open, patch

from pygpt_net.ui.dialog.license import License


def _window():
    values = {}
    config = SimpleNamespace(
        get_app_path=MagicMock(return_value="/app"),
        get=MagicMock(side_effect=lambda key, default=None: values.get(key, default)),
        set=MagicMock(side_effect=lambda key, value: values.__setitem__(key, value)),
        save=MagicMock(),
    )
    quick_start = SimpleNamespace(open=MagicMock())
    return SimpleNamespace(
        core=SimpleNamespace(config=config),
        ui=SimpleNamespace(
            nodes={},
            dialog={},
            dialogs=SimpleNamespace(quick_start=quick_start),
        ),
    )


def test_setup_loads_license_and_registers_dialog():
    window = _window()
    textarea = MagicMock()
    button = MagicMock()
    label = MagicMock()
    dialog = MagicMock()
    with patch("builtins.open", mock_open(read_data="MIT CONTENT")) as opened, \
         patch("pygpt_net.ui.dialog.license.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.license.QPushButton", return_value=button), \
         patch("pygpt_net.ui.dialog.license.QLabel", return_value=label), \
         patch("pygpt_net.ui.dialog.license.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.license.LicenseDialog", return_value=dialog), \
         patch("pygpt_net.ui.dialog.license.trans", side_effect=lambda key: key):
        License(window).setup()

    opened.assert_called_once_with("/app/LICENSE", "r", encoding="utf-8")
    textarea.setReadOnly.assert_called_once_with(True)
    textarea.setPlainText.assert_called_once_with("MIT CONTENT")
    assert window.ui.nodes["dialog.license.accept"] is button
    assert window.ui.nodes["dialog.license.label"] is label
    assert window.ui.dialog["info.license"] is dialog
    dialog.setWindowTitle.assert_called_once_with("dialog.license.title")


def test_setup_uses_empty_text_when_license_read_fails():
    window = _window()
    textarea = MagicMock()
    with patch("builtins.open", side_effect=OSError("no file")), \
         patch("pygpt_net.ui.dialog.license.QPlainTextEdit", return_value=textarea), \
         patch("pygpt_net.ui.dialog.license.QPushButton", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.license.QLabel", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.license.QVBoxLayout", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.license.LicenseDialog", return_value=MagicMock()), \
         patch("pygpt_net.ui.dialog.license.trans", side_effect=lambda key: key), \
         patch("builtins.print"):
        License(window).setup()
    textarea.setPlainText.assert_called_once_with("")


def test_accept_persists_flag_closes_dialog_and_schedules_quick_start():
    window = _window()
    dlg = MagicMock()
    window.ui.dialog["info.license"] = dlg

    with patch("pygpt_net.ui.dialog.license.QTimer.singleShot") as single_shot:
        License(window).accept()

    window.core.config.set.assert_has_calls([
        call("license.accepted", True),
        call("quick_start.pending", True),
    ])
    window.core.config.save.assert_called_once_with()
    dlg.close.assert_called_once_with()
    single_shot.assert_called_once_with(0, window.ui.dialogs.quick_start.open)
