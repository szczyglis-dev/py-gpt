from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.vision import camera as camera_module
from pygpt_net.ui.widget.vision.camera import VideoLabel


def _label():
    return SimpleNamespace(
        _freeze_duration_ms=1000,
        _freeze=MagicMock(), _freeze_effect=MagicMock(), _freeze_timer=MagicMock(),
        _freeze_fade_out=MagicMock(), _flash=MagicMock(), _flash_effect=MagicMock(),
        _flash_anim=MagicMock(),
        grab=MagicMock(return_value="shot"), rect=MagicMock(return_value="rect"),
        window=SimpleNamespace(controller=SimpleNamespace(camera=MagicMock())),
        _start_freeze=MagicMock(), _start_flash=MagicMock(),
    )


def test_start_freeze_snapshots_and_starts_timer():
    label = _label()
    label._freeze_fade_out.state.return_value = 0
    with patch("pygpt_net.ui.widget.vision.camera.QAbstractAnimation", SimpleNamespace(Stopped=0)):
        VideoLabel._start_freeze(label, 250)
    label.grab.assert_called_once_with()
    label._freeze_timer.stop.assert_called_once_with()
    label._freeze_effect.setOpacity.assert_called_once_with(1.0)
    label._freeze.setGeometry.assert_called_once_with("rect")
    label._freeze.setPixmap.assert_called_once_with("shot")
    label._freeze.show.assert_called_once_with()
    label._freeze_timer.start.assert_called_once_with(250)


def test_freeze_timeout_only_starts_fade_when_visible():
    label = _label()
    label._freeze.isVisible.return_value = False
    VideoLabel._on_freeze_timeout(label)
    label._freeze_fade_out.start.assert_not_called()
    label._freeze.isVisible.return_value = True
    VideoLabel._on_freeze_timeout(label)
    label._freeze_fade_out.start.assert_called_once_with()


def test_freeze_finished_hides_clears_and_resets_opacity():
    label = _label()
    VideoLabel._on_freeze_finished(label)
    label._freeze.hide.assert_called_once_with()
    label._freeze.clear.assert_called_once_with()
    label._freeze_effect.setOpacity.assert_called_once_with(1.0)


def test_start_flash_restarts_running_animation():
    label = _label()
    label._flash_anim.state.return_value = 1
    with patch("pygpt_net.ui.widget.vision.camera.QAbstractAnimation", SimpleNamespace(Stopped=0)):
        VideoLabel._start_flash(label)
    label._flash.setGeometry.assert_called_once_with("rect")
    label._flash.show.assert_called_once_with()
    label._flash_effect.setOpacity.assert_called_once_with(0.0)
    label._flash_anim.stop.assert_called_once_with()
    label._flash_anim.start.assert_called_once_with()


def test_left_click_starts_effects_and_defers_manual_capture():
    window = SimpleNamespace(controller=SimpleNamespace(camera=MagicMock()))
    label = MagicMock(spec=VideoLabel)
    label.window = window
    event = MagicMock()
    event.button.return_value = Qt.LeftButton
    with patch("pygpt_net.ui.widget.vision.camera.QTimer.singleShot", create=True) as single, \
         patch.object(camera_module.QLabel, "mousePressEvent", create=True):
        VideoLabel.mousePressEvent(label, event)
    label._start_freeze.assert_called_once_with()
    label._start_flash.assert_called_once_with()
    delay, callback = single.call_args.args
    assert delay == 0
    callback()
    window.controller.camera.manual_capture.assert_called_once_with()
