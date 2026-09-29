from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.dialog.confirm import ConfirmDialog


def test_confirm_button_order_is_windows_specific():
    widget = SimpleNamespace()
    with patch("pygpt_net.ui.widget.dialog.confirm.sys.platform", "win32"):
        assert ConfirmDialog._affirmative_on_left(widget) is True
    with patch("pygpt_net.ui.widget.dialog.confirm.sys.platform", "linux"):
        assert ConfirmDialog._affirmative_on_left(widget) is False
    with patch("pygpt_net.ui.widget.dialog.confirm.sys.platform", "darwin"):
        assert ConfirmDialog._affirmative_on_left(widget) is False


def test_neutral_default_sets_no_button_as_only_default():
    yes = MagicMock()
    no = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(nodes={
        "dialog.confirm.btn.yes": yes,
        "dialog.confirm.btn.no": no,
    })))

    ConfirmDialog._apply_neutral_default(widget)

    yes.setAutoDefault.assert_called_once_with(False)
    yes.setDefault.assert_called_once_with(False)
    no.setAutoDefault.assert_called_once_with(True)
    no.setDefault.assert_called_once_with(True)
    no.setFocus.assert_called_once()


def test_neutral_default_is_safe_when_buttons_are_missing():
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(nodes={})))
    ConfirmDialog._apply_neutral_default(widget)
