from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.audio.input_button import AudioInputButton, VoiceControlButton


def test_voice_status_and_layout_helpers_delegate():
    widget = SimpleNamespace(status=MagicMock(), layout=MagicMock())
    VoiceControlButton.set_status(widget, "Listening")
    VoiceControlButton.add_widget(widget, "extra")
    widget.status.setText.assert_called_once_with("Listening")
    widget.layout.addWidget.assert_called_once_with("extra")


def test_voice_toggle_dispatches_voice_control_event():
    window = SimpleNamespace(dispatch=MagicMock())
    widget = SimpleNamespace(window=window)
    fake_event = object()
    app_event = MagicMock(return_value=fake_event)
    app_event.VOICE_CONTROL_TOGGLE = "voice-toggle"

    with patch("pygpt_net.ui.widget.audio.input_button.AppEvent", app_event):
        VoiceControlButton.toggle_recording(widget)

    app_event.assert_called_once_with("voice-toggle")
    window.dispatch.assert_called_once_with(fake_event)


def test_audio_input_add_widget_delegates_to_layout():
    widget = SimpleNamespace(layout=MagicMock())
    AudioInputButton.add_widget(widget, "extra")
    widget.layout.addWidget.assert_called_once_with("extra")


def test_audio_input_toggle_dispatches_record_toggle_event():
    window = SimpleNamespace(dispatch=MagicMock())
    widget = SimpleNamespace(window=window)
    fake_event = object()
    event_cls = MagicMock(return_value=fake_event)
    event_cls.AUDIO_INPUT_RECORD_TOGGLE = "record-toggle"

    with patch("pygpt_net.ui.widget.audio.input_button.Event", event_cls):
        AudioInputButton.toggle_recording(widget)

    event_cls.assert_called_once_with("record-toggle")
    window.dispatch.assert_called_once_with(fake_event)
