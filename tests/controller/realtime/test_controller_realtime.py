from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.controller.realtime.realtime import Realtime
from pygpt_net.core.events import AppEvent, Event, KernelEvent, RealtimeEvent, RenderEvent
from pygpt_net.core.tabs import Tab
from pygpt_net.core.types import MODE_AUDIO


def _realtime():
    realtime = Realtime.__new__(Realtime)
    realtime.window = MagicMock()
    realtime.manager = MagicMock()
    realtime.signals = MagicMock()
    realtime.current_active = None
    realtime.allowed_modes = [MODE_AUDIO]
    realtime.manual_commit_sent = False
    realtime._continuation_text_started = set()
    realtime.window.core.config.get.side_effect = lambda key, default=None: {
        "mode": MODE_AUDIO,
        "audio.input.loop": False,
        "audio.input.auto_turn": True,
    }.get(key, default)
    realtime.window.controller.ui.tabs.get_current_type.return_value = Tab.TAB_CHAT
    realtime.window.controller.audio.is_muted.return_value = False
    return realtime


def test_realtime_setup_delegates_to_audio_core():
    realtime = _realtime()

    realtime.setup()

    realtime.window.core.audio.setup.assert_called_once_with()


def test_realtime_is_enabled_only_in_audio_mode_outside_notepad():
    realtime = _realtime()

    assert realtime.is_enabled() is True

    realtime.window.controller.ui.tabs.get_current_type.return_value = Tab.TAB_NOTEPAD
    assert realtime.is_enabled() is False

    realtime.window.core.config.get.side_effect = lambda key, default=None: "chat" if key == "mode" else default
    assert realtime.is_enabled() is False


def test_realtime_unsupported_realtime_event_is_stopped_without_side_effects():
    realtime = _realtime()
    realtime.allowed_modes = []
    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_DELTA, {"payload": b"x"})

    realtime.handle(event)

    assert event.stop is True
    realtime.window.core.audio.output.handle_realtime.assert_not_called()


def test_realtime_audio_output_delta_forwards_payload_unless_muted():
    realtime = _realtime()
    realtime.set_idle = MagicMock()
    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_DELTA, {"payload": b"audio"})

    realtime.handle(event)
    realtime.window.core.audio.output.handle_realtime.assert_called_once_with(b"audio", realtime.signals)
    realtime.set_idle.assert_called_once_with()

    realtime.window.core.audio.output.handle_realtime.reset_mock()
    realtime.window.controller.audio.is_muted.return_value = True
    realtime.handle(event)
    realtime.window.core.audio.output.handle_realtime.assert_not_called()


@pytest.mark.parametrize(
    "provider,api_attr",
    [("google", "google"), ("openai", "openai"), ("x_ai", "xai")],
)
def test_realtime_audio_input_routes_to_active_provider(provider, api_attr):
    realtime = _realtime()
    realtime.current_active = provider
    realtime.set_idle = MagicMock()
    event = RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_DELTA, {"payload": b"a"})

    realtime.handle(event)

    getattr(realtime.window.core.api, api_attr).realtime.handle_audio_input.assert_called_once_with(event)


def test_realtime_ready_and_text_delta_dispatch_render_events():
    realtime = _realtime()
    realtime.set_busy = MagicMock()
    realtime.set_idle = MagicMock()
    ctx = SimpleNamespace(meta=SimpleNamespace(id=1))

    realtime.handle(RealtimeEvent(RealtimeEvent.RT_OUTPUT_READY, {"ctx": ctx}))
    ready_event = realtime.window.dispatch.call_args.args[0]
    assert isinstance(ready_event, RenderEvent)
    assert ready_event.name == RenderEvent.STREAM_BEGIN
    realtime.set_busy.assert_called_once_with()

    realtime.window.dispatch.reset_mock()
    realtime.handle(RealtimeEvent(RealtimeEvent.RT_OUTPUT_TEXT_DELTA, {"ctx": ctx, "chunk": "hello"}))
    delta_event = realtime.window.dispatch.call_args.args[0]
    assert isinstance(delta_event, RenderEvent)
    assert delta_event.name == RenderEvent.STREAM_APPEND
    assert delta_event.data["chunk"] == "hello"


def test_realtime_audio_commit_stops_input_once_and_resets_manual_commit_flag():
    realtime = _realtime()
    realtime.set_busy = MagicMock()
    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT)

    realtime.handle(event)
    realtime.window.controller.audio.execute_input_stop.assert_called_once_with()

    realtime.window.controller.audio.execute_input_stop.reset_mock()
    realtime.manual_commit_sent = True
    realtime.handle(event)
    realtime.window.controller.audio.execute_input_stop.assert_not_called()
    assert realtime.manual_commit_sent is False


def test_realtime_manual_stop_and_start_schedule_commit_and_dispatch_status():
    realtime = _realtime()
    realtime.set_busy = MagicMock()
    realtime.set_idle = MagicMock()
    realtime.manual_commit = MagicMock()

    with patch("pygpt_net.controller.realtime.realtime.QTimer.singleShot", side_effect=lambda delay, fn: fn()), \
            patch("pygpt_net.controller.realtime.realtime.trans", return_value="Listening"):
        realtime.handle(RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_MANUAL_STOP))
        assert realtime.manual_commit_sent is True
        realtime.manual_commit.assert_called_once_with()

        realtime.handle(RealtimeEvent(RealtimeEvent.RT_INPUT_AUDIO_MANUAL_START))

    realtime.window.controller.chat.input.execute.assert_called_once_with("...", force=True)
    status_event = realtime.window.dispatch.call_args.args[0]
    assert isinstance(status_event, KernelEvent)
    assert status_event.name == KernelEvent.STATUS
    assert status_event.data["status"] == "Listening"


def test_realtime_audio_end_unlocks_input_and_schedules_next_turn_only_in_loop():
    realtime = _realtime()
    realtime.set_idle = MagicMock()
    realtime.is_loop = MagicMock(return_value=True)
    realtime.next_turn = MagicMock()

    with patch("pygpt_net.controller.realtime.realtime.QTimer.singleShot", side_effect=lambda delay, fn: fn()) as single_shot:
        realtime.handle(RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_END))

    realtime.window.controller.chat.common.unlock_input.assert_called_once_with()
    realtime.next_turn.assert_called_once_with()
    single_shot.assert_called_once()


def test_realtime_turn_end_finalizes_context_updates_status_and_unlocks():
    realtime = _realtime()
    realtime.end_turn = MagicMock()
    realtime.set_idle = MagicMock()
    realtime.window.controller.audio.is_recording.return_value = True
    ctx = MagicMock()

    with patch("pygpt_net.controller.realtime.realtime.trans", return_value="Listening"):
        realtime.handle(RealtimeEvent(RealtimeEvent.RT_OUTPUT_TURN_END, {"ctx": ctx}))

    realtime.end_turn.assert_called_once_with(ctx)
    realtime.window.update_status.assert_called_once_with("Listening")
    realtime.window.controller.chat.common.unlock_input.assert_called_once_with()


def test_realtime_volume_and_error_paths_do_not_touch_real_audio_device():
    realtime = _realtime()
    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_VOLUME_CHANGED, {"volume": 0.25})
    realtime.handle(event)
    realtime.window.controller.audio.ui.on_output_volume_change.assert_called_once_with(0.25)

    realtime.window.controller.audio.ui.on_output_volume_change.reset_mock()
    realtime.window.controller.audio.is_muted.return_value = True
    realtime.handle(event)
    realtime.window.controller.audio.ui.on_output_volume_change.assert_called_once_with(0.0)

    realtime.set_idle = MagicMock()
    error = RuntimeError("audio")
    realtime.handle(RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_ERROR, {"error": error}))
    realtime.window.core.debug.log.assert_called_once_with(error)
    realtime.window.controller.chat.common.unlock_input.assert_called_once_with()


def test_realtime_app_events_schedule_reset_without_realtime_mode_guard():
    realtime = _realtime()
    realtime.allowed_modes = []
    realtime.reset = MagicMock()
    realtime.window.core.config.get.side_effect = lambda key, default=None: "chat" if key == "mode" else default

    with patch("pygpt_net.controller.realtime.realtime.QTimer.singleShot", side_effect=lambda delay, fn: fn()):
        realtime.handle(AppEvent(AppEvent.MODE_SELECTED))
        realtime.handle(AppEvent(AppEvent.CTX_CREATED))
        realtime.handle(AppEvent(AppEvent.CTX_SELECTED))

    assert realtime.reset.call_count == 3


def test_realtime_next_turn_toggles_recording_and_defers_listening_status():
    realtime = _realtime()
    realtime.window.controller.audio.is_recording.return_value = True

    with patch("pygpt_net.controller.realtime.realtime.QTimer.singleShot", side_effect=lambda delay, fn: fn()), \
            patch("pygpt_net.controller.realtime.realtime.trans", return_value="Listening"):
        realtime.next_turn()

    event = realtime.window.dispatch.call_args.args[0]
    assert isinstance(event, Event)
    assert event.name == Event.AUDIO_INPUT_RECORD_TOGGLE
    realtime.window.update_status.assert_called_once_with("Listening")


def test_realtime_loop_auto_turn_and_support_flags_use_config_and_kernel_state():
    realtime = _realtime()
    realtime.window.controller.kernel.stopped.return_value = True
    assert realtime.is_loop() is False

    realtime.window.controller.kernel.stopped.return_value = False
    realtime.window.core.config.get.side_effect = lambda key, default=None: {
        "mode": MODE_AUDIO,
        "audio.input.loop": True,
        "audio.input.auto_turn": False,
    }.get(key, default)
    assert realtime.is_loop() is True
    assert realtime.is_auto_turn() is False
    assert realtime.is_supported() is True


def test_realtime_handle_response_forwards_event_to_kernel_listener():
    realtime = _realtime()
    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_READY)

    realtime.handle_response(event)

    realtime.window.controller.kernel.listener.assert_called_once_with(event)


@pytest.mark.parametrize(
    "provider,api_attr",
    [("google", "google"), ("openai", "openai"), ("x_ai", "xai")],
)
def test_realtime_manual_commit_routes_to_active_provider(provider, api_attr):
    realtime = _realtime()
    realtime.current_active = provider

    realtime.manual_commit()

    getattr(realtime.window.core.api, api_attr).realtime.manual_commit.assert_called_once_with()


def test_realtime_end_turn_calls_all_chat_output_stages():
    realtime = _realtime()
    realtime.set_idle = MagicMock()
    ctx = SimpleNamespace(meta=MagicMock(), turn_parent=None)

    realtime.end_turn(ctx)

    realtime.window.controller.chat.output.handle_after.assert_called_once_with(ctx=ctx, mode=MODE_AUDIO, stream=True)
    realtime.window.controller.chat.output.post_handle.assert_called_once_with(ctx=ctx, mode=MODE_AUDIO, stream=True)
    realtime.window.controller.chat.output.handle_end.assert_called_once_with(ctx=ctx, mode=MODE_AUDIO)
    realtime.window.controller.chat.common.show_response_tokens.assert_called_once_with(ctx)


def test_realtime_shutdown_and_reset_mock_provider_boundaries_and_log_errors():
    realtime = _realtime()
    realtime.window.core.api.google.realtime.shutdown.side_effect = RuntimeError("g")
    realtime.window.core.api.xai.realtime.reset.side_effect = RuntimeError("x")

    realtime.shutdown()
    realtime.window.core.api.openai.realtime.shutdown.assert_called_once_with()
    realtime.window.core.api.google.realtime.shutdown.assert_called_once_with()
    realtime.window.core.api.xai.realtime.shutdown.assert_called_once_with()
    realtime.manager.shutdown.assert_called_once_with()

    realtime.reset()
    realtime.window.core.api.openai.realtime.reset.assert_called_once_with()
    realtime.window.core.api.google.realtime.reset.assert_called_once_with()
    realtime.window.core.api.xai.realtime.reset.assert_called_once_with()
    assert realtime.window.core.debug.log.call_count == 2


def test_realtime_set_current_active_normalizes_provider_name():
    realtime = _realtime()

    realtime.set_current_active("OpenAI")
    assert realtime.current_active == "openai"
    realtime.set_current_active(None)
    assert realtime.current_active is None


def test_realtime_set_idle_and_busy_dispatch_kernel_state_events_via_timer():
    realtime = _realtime()

    with patch("pygpt_net.controller.realtime.realtime.QTimer.singleShot", side_effect=lambda delay, fn: fn()):
        realtime.set_idle()
        realtime.set_busy()

    idle = realtime.window.dispatch.call_args_list[0].args[0]
    busy = realtime.window.dispatch.call_args_list[1].args[0]
    assert idle.name == KernelEvent.STATE_IDLE
    assert idle.data["id"] == "realtime"
    assert busy.name == KernelEvent.STATE_BUSY
    assert busy.data["id"] == "realtime"
