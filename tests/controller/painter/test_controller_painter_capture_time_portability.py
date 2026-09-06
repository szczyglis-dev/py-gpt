import datetime as dt
import os
from unittest.mock import MagicMock, patch

from pygpt_net.controller.painter.capture import Capture
from pygpt_net.core.events import KernelEvent


FIXED_NOW = dt.datetime(2025, 1, 2, 3, 4, 5)


class FixedDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXED_NOW
        return FIXED_NOW.replace(tzinfo=dt.timezone.utc).astimezone(tz)


def _capture():
    window = MagicMock()
    window.controller.attachment.is_capture_clear.return_value = False
    window.controller.painter.common.get_capture_dir.return_value = "/capture"
    window.core.config.get.return_value = "chat"
    capture = Capture(window)
    capture.attach = MagicMock()
    return capture, window


def test_painter_screenshot_playwright_uses_fixed_clock_and_mocks_browser_page():
    capture, window = _capture()
    page = MagicMock()
    expected_name = "cap-2025-01-02_03-04-05"
    expected_path = os.path.join("/capture", expected_name + ".png")

    with patch("pygpt_net.controller.painter.capture.datetime.datetime", FixedDateTime), \
            patch("pygpt_net.controller.painter.capture.trans", side_effect=lambda key: key):
        result = capture.screenshot_playwright(page, silent=False)

    assert result == expected_path
    page.screenshot.assert_called_once_with(path=expected_path, full_page=False)
    capture.attach.assert_called_once_with(expected_name, expected_path, "screenshot", silent=False)
    window.controller.painter.open.assert_called_once_with(expected_path)
    event = window.dispatch.call_args.args[0]
    assert isinstance(event, KernelEvent)
    assert "2025-01-02 03:04:05" in event.data["status"]


def test_painter_use_uses_fixed_clock_without_wall_clock_assumption():
    capture, window = _capture()
    expected_name = "cap-2025-01-02_03-04-05"
    expected_path = os.path.join("/capture", expected_name + ".png")

    with patch("pygpt_net.controller.painter.capture.datetime.datetime", FixedDateTime), \
            patch("pygpt_net.controller.painter.capture.trans", side_effect=lambda key: key):
        assert capture.use() is True

    window.ui.painter.image.save.assert_called_once_with(expected_path)
    capture.attach.assert_called_once_with(expected_name, expected_path)
    event = window.dispatch.call_args.args[0]
    assert "2025-01-02 03:04:05" in event.data["status"]
