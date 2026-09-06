from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pygpt_net.controller.chat.common import Common
from pygpt_net.core.events import AppEvent, Event, KernelEvent, RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT, MODE_AUDIO


def _common():
    common = Common.__new__(Common)
    common.window = MagicMock()
    common.initialized = False
    common.counter = 0.0
    common._t0 = None
    common._shortener = None
    common.window.ui.nodes = {
        "input": MagicMock(),
        "input.stream": MagicMock(),
        "input.send_shift_enter": MagicMock(),
        "input.send_enter": MagicMock(),
        "cmd.enabled": MagicMock(),
        "output.timestamp": MagicMock(),
        "output.raw": MagicMock(),
        "output": {},
        "output_plain": {},
        "input.send_btn": MagicMock(),
        "input.stop_btn": MagicMock(),
        "start.api_key.provider": MagicMock(),
    }
    return common


def test_chat_common_setup_migrates_invalid_send_mode_and_dispatches_renderer_switch():
    common = _common()
    values = {
        "stream": True,
        "send_mode": 0,
        "cmd": False,
        "output_timestamp": True,
        "render.plain": False,
    }
    common.window.core.config.get.side_effect = lambda key, default=None: values.get(key, default)

    common.setup()

    common.window.core.config.set.assert_called_once_with("send_mode", 1)
    common.window.ui.nodes["input.stream"].setChecked.assert_called_once_with(True)
    common.window.ui.nodes["input.send_enter"].setChecked.assert_called_once_with(True)
    common.window.ui.nodes["input.send_shift_enter"].setChecked.assert_called_once_with(False)
    events = [c.args[0] for c in common.window.dispatch.call_args_list]
    assert events[0].name == RenderEvent.ON_TS_ENABLE
    assert events[-1].name == RenderEvent.ON_SWITCH
    common.window.ui.nodes["input"].setFocus.assert_called_once_with()
    assert common.initialized is True


def test_chat_common_append_to_input_uses_qtextcursor_without_real_clipboard_or_io():
    common = _common()
    node = common.window.ui.nodes["input"]
    cursor = MagicMock()
    node.toPlainText.return_value = "existing"
    node.textCursor.return_value = cursor

    common.append_to_input(" line1\nline2 ", separator=" ")

    inserted = [c.args[0] for c in cursor.insertText.call_args_list]
    assert inserted == [" line1", "line2"]
    cursor.insertBlock.assert_called_once_with()
    node.setTextCursor.assert_called_once_with(cursor)
    node.setFocus.assert_called_once_with()
    common.window.controller.ui.update_tokens.assert_called_once_with()


def test_chat_common_basic_toggles_update_config_and_command_state():
    common = _common()

    common.toggle_stream(True)
    common.window.core.config.set.assert_called_with("stream", True)

    common.toggle_cmd(False)
    common.window.core.config.set.assert_called_with("cmd", False)
    assert common.window.controller.command.stop is True
    common.window.controller.ui.update.assert_called_once_with()

    common.toggle_send_shift(99)
    common.window.core.config.set.assert_called_with("send_mode", 1)
    common.window.ui.nodes["input.send_enter"].setChecked.assert_called_with(True)


def test_chat_common_focus_lock_and_unlock_update_input_state():
    common = _common()

    common.focus_input()
    common.lock_input()
    assert common.window.controller.chat.input.locked is True
    common.window.ui.nodes["input.send_btn"].setEnabled.assert_called_with(False)
    common.window.ui.nodes["input.stop_btn"].setVisible.assert_called_with(True)

    common.unlock_input()
    assert common.window.controller.chat.input.locked is False
    assert common.window.controller.chat.input.generating is False
    common.window.ui.nodes["input.send_btn"].setEnabled.assert_called_with(True)
    common.window.ui.nodes["input.stop_btn"].setVisible.assert_called_with(False)


def test_chat_common_can_unlock_rejects_agents_waiting_stack_or_pending_commands():
    common = _common()
    ctx = MagicMock()
    ctx.has_commands.return_value = False
    common.window.core.config.get.return_value = "chat"
    common.window.controller.agent.legacy.enabled.return_value = False
    common.window.controller.agent.experts.enabled.return_value = False
    common.window.core.experts.has_calls.return_value = False
    common.window.controller.kernel.stack.waiting.return_value = False

    assert common.can_unlock(ctx) is True

    common.window.controller.kernel.stack.waiting.return_value = True
    assert common.can_unlock(ctx) is False
    common.window.controller.kernel.stack.waiting.return_value = False

    ctx.has_commands.return_value = True
    assert common.can_unlock(ctx) is False


def test_chat_common_handle_stop_prioritizes_active_audio_input_recording():
    common = _common()
    common.window.controller.access.voice.is_recording = False
    handler = MagicMock()
    handler.is_recording = True
    common.window.core.plugins.get.return_value.handler_simple = handler

    common.handle_stop()

    event = common.window.dispatch.call_args.args[0]
    assert isinstance(event, Event)
    assert event.name == Event.AUDIO_INPUT_RECORD_TOGGLE
    common.window.controller.audio.stop_output.assert_not_called()
    common.window.controller.kernel.stop.assert_not_called()


def test_chat_common_handle_stop_stops_voice_then_output_and_kernel_when_no_audio_input_recording():
    common = _common()
    common.window.controller.access.voice.is_recording = True
    handler = MagicMock()
    handler.is_recording = False
    common.window.core.plugins.get.return_value.handler_simple = handler

    common.handle_stop()

    common.window.controller.access.voice.stop_recording.assert_called_once_with(timeout=True)
    common.window.controller.audio.stop_output.assert_called_once_with()
    common.window.controller.kernel.stop.assert_called_once_with()


def test_chat_common_auto_unlock_respects_audio_mode_and_kernel_stop():
    common = _common()
    ctx = MagicMock()
    common.can_unlock = MagicMock(return_value=True)
    common.unlock_input = MagicMock()
    common.window.controller.kernel.stopped.return_value = False
    common.window.core.config.get.return_value = "chat"

    assert common.auto_unlock(ctx) is True
    common.unlock_input.assert_called_once_with()

    common.unlock_input.reset_mock()
    common.window.core.config.get.return_value = MODE_AUDIO
    assert common.auto_unlock(ctx) is False
    common.unlock_input.assert_not_called()


def test_chat_common_stop_dispatches_shutdown_events_and_mocks_external_api_stop():
    common = _common()
    common.unlock_input = MagicMock()
    common.stop_client = MagicMock()
    common.reset_counter = MagicMock()
    common.window.core.config.get.return_value = "chat"

    with patch("pygpt_net.controller.chat.common.QApplication.processEvents"), \
            patch("pygpt_net.controller.chat.common.trans", return_value="Stopped"):
        common.stop(exit=False)

    names = [c.args[0].name for c in common.window.dispatch.call_args_list]
    assert Event.FORCE_STOP in names
    assert Event.AUDIO_INPUT_TOGGLE in names
    assert RenderEvent.TOOL_END in names
    assert KernelEvent.STATE_IDLE in names
    assert AppEvent.INPUT_STOPPED in names
    common.window.controller.kernel.stack.clear.assert_called_once_with()
    common.window.controller.agent.experts.stop.assert_called_once_with()
    common.window.controller.agent.legacy.on_stop.assert_called_once_with()
    common.window.controller.assistant.threads.reset.assert_called_once_with()
    common.unlock_input.assert_called_once_with()
    common.stop_client.assert_called_once_with()
    common.reset_counter.assert_called_once_with()


def test_chat_common_stop_attempts_remote_assistant_stop_only_outside_exit():
    common = _common()
    common.unlock_input = MagicMock()
    common.stop_client = MagicMock()
    common.reset_counter = MagicMock()
    common.window.core.config.get.return_value = MODE_ASSISTANT

    with patch("pygpt_net.controller.chat.common.QApplication.processEvents"), \
            patch("pygpt_net.controller.chat.common.trans", return_value="Stopped"):
        common.stop(exit=False)
    common.window.controller.assistant.run_stop.assert_called_once_with()

    common.window.controller.assistant.run_stop.reset_mock()
    common.stop(exit=True)
    common.window.controller.assistant.run_stop.assert_not_called()


def test_chat_common_stop_client_swallows_external_api_error():
    common = _common()
    common.window.core.api.stop.side_effect = RuntimeError("client")

    common.stop_client()

    common.window.core.api.stop.assert_called_once_with()


@pytest.mark.parametrize(
    "provider,key",
    [
        ("anthropic", "api_key_anthropic"),
        ("google", "api_key_google"),
        ("x_ai", "api_key_xai"),
        ("perplexity", "api_key_perplexity"),
        ("deepseek_api", "api_key_deepseek"),
        ("mistral_ai", "api_key_mistral"),
    ],
)
def test_chat_common_check_api_key_rejects_missing_remote_provider_key(provider, key):
    common = _common()
    model = MagicMock()
    model.provider = provider
    model.is_ollama.return_value = False
    common.window.core.config.get.side_effect = lambda name, default=None: None if name == key else "other"
    common.window.core.llm.get_provider_name.return_value = "Provider"

    assert common.check_api_key("chat", model, monit=True) is False
    common.window.controller.launcher.show_api_monit.assert_called_once_with()
    common.window.update_status.assert_called_once_with("Missing API KEY for provider: Provider")


def test_chat_common_check_api_key_allows_local_and_non_gpt_openai_without_key():
    common = _common()
    local = MagicMock()
    local.is_ollama.return_value = True
    assert common.check_api_key("chat", local) is True

    model = MagicMock()
    model.provider = "openai"
    model.is_ollama.return_value = False
    model.is_gpt.return_value = False
    common.window.core.config.get.return_value = ""
    assert common.check_api_key("chat", model) is True


def test_chat_common_toggle_render_options_dispatch_expected_events():
    common = _common()

    common.toggle_timestamp(True)
    event = common.window.dispatch.call_args.args[0]
    assert event.name == RenderEvent.ON_TS_ENABLE

    common.toggle_edit_icons(False)
    event = common.window.dispatch.call_args.args[0]
    assert event.name == RenderEvent.ON_EDIT_DISABLE

    common.toggle_raw(True)
    event = common.window.dispatch.call_args.args[0]
    assert event.name == RenderEvent.ON_SWITCH
    common.window.controller.config.checkbox.apply.assert_called_once_with(
        "config", "render.plain", {"value": True}
    )
    common.window.controller.ui.update_font_size.assert_called_once_with()


def test_chat_common_save_text_mocks_file_dialog_and_filesystem_boundary():
    common = _common()
    common.window.core.config.get_last_used_dir.return_value = "/old"
    m = mock_open()

    with patch("pygpt_net.controller.chat.common.QFileDialog.Options", return_value="opts"), \
            patch("pygpt_net.controller.chat.common.QFileDialog.getSaveFileName", return_value=("/tmp/out.txt", "")) as dialog, \
            patch("builtins.open", m), \
            patch("pygpt_net.controller.chat.common.trans", return_value="Saved"):
        common.save_text("  hello  ")

    common.window.core.config.set_last_used_dir.assert_called_once_with("/tmp")
    m.assert_called_once_with("/tmp/out.txt", "w", encoding="utf-8")
    m().write.assert_called_once_with("hello")
    common.window.update_status.assert_called_once_with("Saved: out.txt")


def test_chat_common_counter_uses_mocked_monotonic_perf_counter_without_sleep():
    common = _common()

    with patch("pygpt_net.controller.chat.common.perf_counter", side_effect=[100.0, 102.5, 105.0, 107.0, 109.0]):
        common.start_counter()
        assert common.get_counter() == 2.5
        assert common.stop_counter() == 5.0
        common.start_counter()
        assert common.stop_counter() == 2.0


def test_chat_common_stop_counter_requires_started_timer():
    common = _common()

    with pytest.raises(RuntimeError, match="Timer was not started"):
        common.stop_counter()


def test_chat_common_tokens_per_second_and_duration_formatting_cover_boundaries():
    common = _common()

    assert common.tokens_per_second(100, seconds=4) == 25.0
    assert common.tokens_per_second(100, seconds=0) == 0.0
    assert common.format_duration(0.8) == "800ms"
    assert common.format_duration(12.9) == "12s"
    assert common.format_duration(72) == "1m 12s"
    assert common.format_duration(3 * 3600 + 5 * 60) == "3h 5m"
    assert common.format_duration(86400 + 7200, max_units=2) == "1d 2h"


@pytest.mark.parametrize(
    "value,expected",
    [(999, "999"), (15_300, "15.3k"), (2_000_000, "2M"), (3_500_000_000, "3.5B"), (-1_500, "-1.5k")],
)
def test_chat_common_fallback_shorten(value, expected):
    common = _common()
    assert common._fallback_shorten(value) == expected


def test_chat_common_format_stats_uses_optional_shortener_and_counter():
    common = _common()
    common.counter = 4.0
    assert common.format_stats(100) == "25 tokens/s - 4s"

    common._shortener = lambda value: f"S:{value:.1f}"
    assert common.format_stats(100) == "S:25.0 tokens/s - 4s"


def test_chat_common_show_response_tokens_resets_counter_and_formats_status():
    common = _common()
    common.counter = 2.0
    ctx = SimpleNamespace(input_tokens=10, output_tokens=20, total_tokens=30)

    with patch("pygpt_net.controller.chat.common.trans", return_value="Tokens"), \
            patch("pygpt_net.controller.chat.common.short_num", side_effect=lambda value: str(value)):
        common.show_response_tokens(ctx)

    assert common.counter == 0.0
    status = common.window.update_status.call_args.args[0]
    assert status.startswith("Tokens: 10 + 20 = 30")
    assert "tokens/s" in status
