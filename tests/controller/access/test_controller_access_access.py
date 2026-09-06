from unittest.mock import MagicMock, patch

from pygpt_net.controller.access.access import Access
from PySide6.QtCore import Qt

from pygpt_net.core.events import AppEvent, ControlEvent


def _access():
    access = Access.__new__(Access)
    access.window = MagicMock()
    access.control = MagicMock()
    access.voice = MagicMock()
    return access


def test_access_setup_reload_and_update_delegate_to_voice():
    access = _access()

    access.setup()
    access.reload()
    access.update()

    assert access.voice.setup.call_count == 2
    access.voice.update.assert_called_once_with()


def test_access_handle_routes_control_and_app_events_and_stops_propagation():
    access = _access()
    control = ControlEvent(ControlEvent.CTX_NEW)
    app = AppEvent(AppEvent.APP_STARTED)
    access.window.core.access.voice.is_muted.return_value = False

    access.handle(control)
    access.handle(app)

    access.control.handle.assert_called_once_with(control)
    access.voice.play.assert_called_once_with(app)
    assert control.stop is True
    assert app.stop is True


def test_access_handle_app_toggles_recording_and_respects_muted_event():
    access = _access()
    event = AppEvent(AppEvent.VOICE_CONTROL_TOGGLE)
    access.window.core.access.voice.is_muted.return_value = True

    access.handle_app(event)

    access.voice.toggle_recording.assert_called_once_with()
    access.voice.play.assert_not_called()


def test_access_handle_app_plays_unmuted_event():
    access = _access()
    event = AppEvent(AppEvent.APP_STARTED)
    access.window.core.access.voice.is_muted.return_value = False

    access.handle_app(event)

    access.voice.play.assert_called_once_with(event)


def test_access_on_escape_stops_recorders_output_kernel_and_dialog():
    access = _access()
    access.voice.is_recording = True
    input_handler = MagicMock()
    input_handler.is_recording = True
    access.window.core.plugins.get.return_value.handler_simple = input_handler
    access.close_top_dialog_if_any = MagicMock(return_value=True)

    access.on_escape()

    access.voice.stop_recording.assert_called_once_with(timeout=True)
    input_handler.stop_recording.assert_called_once_with(timeout=True)
    access.window.controller.audio.stop_output.assert_called_once_with()
    access.window.controller.kernel.stop.assert_called_once_with()
    access.close_top_dialog_if_any.assert_called_once_with()


def test_access_on_escape_skips_inactive_recorders():
    access = _access()
    access.voice.is_recording = False
    input_handler = MagicMock()
    input_handler.is_recording = False
    access.window.core.plugins.get.return_value.handler_simple = input_handler
    access.close_top_dialog_if_any = MagicMock()

    access.on_escape()

    access.voice.stop_recording.assert_not_called()
    input_handler.stop_recording.assert_not_called()


def test_access_close_top_dialog_prefers_active_modal_widget():
    access = _access()
    top = MagicMock()
    top.windowFlags.return_value = Qt.Dialog
    widget = MagicMock()
    widget.window.return_value = top
    app = MagicMock()
    app.activeModalWidget.return_value = widget

    with patch("pygpt_net.controller.access.access.QApplication.instance", return_value=app):
        result = access.close_top_dialog_if_any()

    assert result is True
    top.close.assert_called_once_with()
    app.activeWindow.assert_not_called()


def test_access_close_top_dialog_returns_false_when_no_dialog_is_available():
    access = _access()
    app = MagicMock()
    app.activeModalWidget.return_value = None
    app.activeWindow.return_value = None

    with patch("pygpt_net.controller.access.access.QApplication.instance", return_value=app), \
            patch("pygpt_net.controller.access.access.QApplication.topLevelWidgets", return_value=[]):
        assert access.close_top_dialog_if_any() is False
