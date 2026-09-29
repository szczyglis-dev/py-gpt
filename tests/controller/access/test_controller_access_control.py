from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.controller.access.control import Control
from pygpt_net.core.events import ControlEvent
from pygpt_net.core.types import MODE_CHAT, MODE_LLAMA_INDEX


def _control():
    control = Control.__new__(Control)
    control.window = MagicMock()
    control.last_confirm = None
    control.ctx_timer = MagicMock()
    control.mode_timer = MagicMock()
    control.ctx_action = None
    control.mode_action = None
    return control


@pytest.mark.parametrize(
    "event_name,target,expected_args",
    [
        (ControlEvent.CTX_NEW, "new", ()),
        (ControlEvent.CTX_PREV, "prev", ()),
        (ControlEvent.CTX_NEXT, "next", ()),
        (ControlEvent.CTX_LAST, "last", ()),
    ],
)
def test_control_handle_ctx_dispatches_deferred_context_actions(event_name, target, expected_args):
    control = _control()
    control.ctx_action = event_name

    control.handle_ctx()

    control.ctx_timer.stop.assert_called_once_with()
    method = getattr(control.window.controller.ctx, target)
    if event_name == ControlEvent.CTX_NEW:
        method.assert_called_once_with(force=True)
    else:
        method.assert_called_once_with()
    assert control.ctx_action is None


@pytest.mark.parametrize(
    "event_name,target,args",
    [
        (ControlEvent.MODE_NEXT, "next", ()),
        (ControlEvent.MODE_PREV, "prev", ()),
        (ControlEvent.MODE_CHAT, "set", (MODE_CHAT,)),
        (ControlEvent.MODE_LLAMA_INDEX, "set", (MODE_LLAMA_INDEX,)),
    ],
)
def test_control_handle_mode_dispatches_deferred_mode_actions(event_name, target, args):
    control = _control()
    control.mode_action = event_name

    control.handle_mode()

    control.mode_timer.stop.assert_called_once_with()
    getattr(control.window.controller.mode, target).assert_called_once_with(*args)
    assert control.mode_action is None


def test_control_handle_app_exit_requires_confirmation_before_closing():
    control = _control()
    event = ControlEvent(ControlEvent.APP_EXIT)

    with patch("pygpt_net.controller.access.control.trans", side_effect=lambda key: f"tr:{key}"):
        control.handle(event)

    assert control.last_confirm is event
    control.window.controller.audio.play_event.assert_called_once_with("tr:event.audio.confirm", event)
    control.window.close.assert_not_called()

    control.handle(event, force=True)
    control.window.close.assert_called_once_with()


def test_control_confirm_replays_last_confirmed_action():
    control = _control()
    pending = ControlEvent(ControlEvent.APP_EXIT)
    control.last_confirm = pending
    event = ControlEvent(ControlEvent.CMD_CONFIRM)
    real_handle = control.handle
    control.handle = MagicMock(wraps=real_handle)

    control.handle(event)

    assert control.handle.call_args_list[-1].args == (pending,)
    assert control.handle.call_args_list[-1].kwargs == {"force": True}
    assert control.last_confirm is None


def test_control_handle_context_actions_start_timers_or_execute_immediately():
    control = _control()
    control.handle_result = MagicMock()

    control.handle(ControlEvent(ControlEvent.CTX_NEXT))
    assert control.ctx_action == ControlEvent.CTX_NEXT
    control.ctx_timer.start.assert_called_once_with(Control.CTX_TIMER_DELAY)

    focus_event = ControlEvent(ControlEvent.CTX_INPUT_FOCUS)
    control.handle(focus_event)
    control.window.controller.chat.common.focus_input.assert_called_once_with()
    control.handle_result.assert_called_once_with(focus_event, True)


def test_control_handle_model_preset_camera_and_audio_plugin_actions():
    control = _control()
    control.handle_result = MagicMock()

    for event_name in (ControlEvent.CAMERA_ENABLE, ControlEvent.CAMERA_DISABLE, ControlEvent.CAMERA_CAPTURE):
        control.handle(ControlEvent(event_name))
    control.window.controller.camera.enable_capture.assert_called_once_with()
    control.window.controller.camera.disable_capture.assert_called_once_with()
    control.window.controller.camera.manual_capture.assert_called_once_with()

    control.handle(ControlEvent(ControlEvent.MODEL_NEXT))
    control.handle(ControlEvent(ControlEvent.MODEL_PREV))
    control.handle(ControlEvent(ControlEvent.PRESET_NEXT))
    control.handle(ControlEvent(ControlEvent.PRESET_PREV))
    control.window.controller.model.next.assert_called_once_with()
    control.window.controller.model.prev.assert_called_once_with()
    control.window.controller.presets.next.assert_called_once_with()
    control.window.controller.presets.prev.assert_called_once_with()

    control.handle(ControlEvent(ControlEvent.AUDIO_INPUT_ENABLE))
    control.handle(ControlEvent(ControlEvent.AUDIO_OUTPUT_DISABLE))
    control.window.controller.plugins.enable.assert_called_once_with("audio_input")
    control.window.controller.plugins.disable.assert_called_once_with("audio_output")
    assert control.handle_result.call_count >= 2


def test_control_handle_input_send_and_append_use_chat_input_without_real_io():
    control = _control()
    control.handle_result = MagicMock()

    send = ControlEvent(ControlEvent.INPUT_SEND, {"params": "hello"})
    control.handle(send)
    control.window.controller.chat.common.clear_input.assert_called_once_with()
    control.window.controller.chat.common.append_to_input.assert_called_once_with("hello")
    control.window.controller.chat.input.send_input.assert_called_once_with()

    control.window.controller.chat.common.append_to_input.reset_mock()
    append = ControlEvent(ControlEvent.INPUT_APPEND, {"params": "world"})
    control.handle(append)
    control.window.controller.chat.common.append_to_input.assert_called_once_with("world")
    control.handle_result.assert_called_with(append, True)


def test_control_handle_notepad_clear_force_extracts_numeric_index():
    control = _control()
    control.handle_result = MagicMock()
    control.window.controller.notepad.clear.return_value = True
    event = ControlEvent(ControlEvent.NOTEPAD_CLEAR, {"params": "note 17"})

    control.handle(event, force=True)

    control.window.controller.notepad.clear.assert_called_once_with(17)
    control.handle_result.assert_called_once_with(event, True)


def test_control_handle_result_respects_speech_setting_and_muted_event():
    control = _control()
    event = ControlEvent(ControlEvent.CTX_INPUT_CLEAR)

    control.window.core.config.get.return_value = False
    control.handle_result(event)
    control.window.controller.audio.play_event.assert_not_called()

    control.window.core.config.get.return_value = True
    control.window.core.access.voice.is_muted.return_value = True
    control.handle_result(event)
    control.window.controller.audio.play_event.assert_not_called()

    control.window.core.access.voice.is_muted.return_value = False
    with patch("pygpt_net.controller.access.control.trans", return_value="spoken"):
        control.handle_result(event)
    control.window.controller.audio.play_event.assert_called_once_with("spoken", event)
