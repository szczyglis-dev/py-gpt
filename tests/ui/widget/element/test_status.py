from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.element.status import BottomStatus


def test_status_text_uses_mocked_clock_not_local_timezone():
    timer = MagicMock()
    msg = MagicMock()
    widget = SimpleNamespace(timer=timer, msg=msg)
    fixed = datetime(2026, 9, 6, 12, 34, 56)

    with patch("pygpt_net.ui.widget.element.status.datetime") as dt:
        dt.now.return_value = fixed
        BottomStatus.set_text(widget, "Ready")

    msg.setText.assert_called_once_with("Ready")
    timer.setText.assert_called_once_with("12:34")


def test_empty_status_clears_timer_without_reading_clock():
    timer = MagicMock()
    msg = MagicMock()
    widget = SimpleNamespace(timer=timer, msg=msg)

    with patch("pygpt_net.ui.widget.element.status.datetime") as dt:
        BottomStatus.set_text(widget, "")

    dt.now.assert_not_called()
    timer.setText.assert_called_once_with("")


def test_status_settext_alias_and_text_accessor():
    widget = SimpleNamespace(set_text=MagicMock(), msg=MagicMock())
    widget.msg.text.return_value = "Current"

    BottomStatus.setText(widget, "Next")

    widget.set_text.assert_called_once_with("Next")
    assert BottomStatus.text(widget) == "Current"
