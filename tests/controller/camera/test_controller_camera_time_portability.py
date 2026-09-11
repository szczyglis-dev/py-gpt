import datetime as dt
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.camera.camera import Camera
from pygpt_net.core.events import KernelEvent


FIXED_NOW = dt.datetime(2025, 1, 2, 3, 4, 5)


class FixedDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXED_NOW
        return FIXED_NOW.replace(tzinfo=dt.timezone.utc).astimezone(tz)


def _camera():
    camera = Camera.__new__(Camera)
    camera.window = MagicMock()
    camera.frame = MagicMock()
    camera.thread_started = True
    camera.is_capture = True
    camera.stop = False
    camera.auto = False
    camera.window.controller.attachment.is_capture_clear.return_value = False
    camera.window.core.config.get_user_dir.return_value = "/capture"
    camera.window.core.filesystem.get_runtime_dir.return_value = "/capture"
    camera.window.core.config.get.side_effect = lambda key, default=None: {
        "vision.capture.quality": 91,
        "mode": "chat",
    }.get(key, default)
    camera.get_current_frame = MagicMock(return_value="rgb-frame")
    return camera


def test_camera_capture_frame_uses_fixed_clock_and_mocks_cv2_boundary():
    camera = _camera()
    camera.window.controller.painter.capture.camera = MagicMock()
    fake_cv2 = SimpleNamespace(IMWRITE_JPEG_QUALITY=1, imwrite=MagicMock())
    expected_name = "cap-2025-01-02_03-04-05"
    expected_path = os.path.join("/capture", expected_name + ".jpg")

    with patch("pygpt_net.controller.camera.camera.datetime.datetime", FixedDateTime), \
            patch("pygpt_net.controller.camera.camera.trans", side_effect=lambda key: key), \
            patch.dict(sys.modules, {"cv2": fake_cv2}):
        result = camera.capture_frame()

    assert result is True
    fake_cv2.imwrite.assert_called_once_with(expected_path, "rgb-frame", [1, 91])
    camera.window.controller.painter.capture.camera.assert_called_once_with(show_flash=False)
    camera.window.core.attachments.new.assert_called_once()
    args = camera.window.core.attachments.new.call_args.args
    assert args[0] == "chat"
    assert args[2] == expected_path
    event = camera.window.dispatch.call_args.args[0]
    assert isinstance(event, KernelEvent)
    assert "2025-01-02 03:04:05" in event.data["status"]


def test_camera_capture_frame_save_uses_fixed_clock_without_sleep_or_real_cv2():
    camera = _camera()
    camera.is_enabled = MagicMock(return_value=True)
    fake_cv2 = SimpleNamespace(IMWRITE_JPEG_QUALITY=1, imwrite=MagicMock())
    expected_path = os.path.join("/capture", "cap-2025-01-02_03-04-05.jpg")

    with patch("pygpt_net.controller.camera.camera.datetime.datetime", FixedDateTime), \
            patch.dict(sys.modules, {"cv2": fake_cv2}):
        result = camera.capture_frame_save()

    assert result == expected_path
    fake_cv2.imwrite.assert_called_once_with(expected_path, "rgb-frame", [1, 91])
    camera.window.core.debug.log.assert_not_called()
