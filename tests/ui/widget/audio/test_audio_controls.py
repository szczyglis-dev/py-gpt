from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.audio.input import AudioInput
from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.audio.input_button import VoiceControlButton, AudioInputButton


def test_audio_input_and_output_helpers_forward_to_layout_and_status():
    for cls in (AudioInput, AudioOutput):
        widget = SimpleNamespace(layout=MagicMock(), status=MagicMock())
        child = object()
        cls.add_widget(widget, child)
        cls.set_status(widget, "ready")
        widget.layout.addWidget.assert_called_once_with(child)
        widget.status.setText.assert_called_once_with("ready")


def test_voice_control_helpers_and_toggle_dispatch_app_event():
    window = SimpleNamespace(dispatch=MagicMock())
    widget = SimpleNamespace(window=window, layout=MagicMock(), status=MagicMock())

    VoiceControlButton.add_widget(widget, "child")
    VoiceControlButton.set_status(widget, "listening")

    with patch("pygpt_net.ui.widget.audio.input_button.AppEvent") as app_event:
        app_event.VOICE_CONTROL_TOGGLE = "voice-toggle"
        app_event.return_value = "event"
        VoiceControlButton.toggle_recording(widget)
        app_event.assert_called_once_with("voice-toggle")
    window.dispatch.assert_called_once_with("event")


def test_audio_input_button_toggle_dispatches_audio_input_record_event():
    window = SimpleNamespace(dispatch=MagicMock())
    widget = SimpleNamespace(window=window, layout=MagicMock())

    with patch("pygpt_net.ui.widget.audio.input_button.Event") as event_cls:
        event_cls.AUDIO_INPUT_RECORD_TOGGLE = "record-toggle"
        event_cls.return_value = "event"
        AudioInputButton.toggle_recording(widget)
        event_cls.assert_called_once_with("record-toggle")
    window.dispatch.assert_called_once_with("event")


def test_audio_input_button_add_widget_delegates_to_layout():
    widget = SimpleNamespace(layout=MagicMock())
    AudioInputButton.add_widget(widget, "child")
    widget.layout.addWidget.assert_called_once_with("child")
