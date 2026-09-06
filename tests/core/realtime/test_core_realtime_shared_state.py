from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.realtime.shared.session import extract_last_session_id, set_ctx_rt_handle, set_rt_session_expires_at
from pygpt_net.core.realtime.shared.text import coalesce_text
from pygpt_net.core.realtime.shared.turn import TurnMode, apply_turn_mode_google, apply_turn_mode_openai


def test_coalesce_text_normalizes_spacing_punctuation_and_newlines():
    assert coalesce_text([]) == ""
    assert coalesce_text([" Hello   ", "world", " !"]) == "Hello world!"
    assert coalesce_text(["first\nsecond", "third"]) == "first\nsecond third"
    assert coalesce_text(["a\n\n\n\nb"]) == "a\n\nb"


def test_turn_modes_mutate_openai_and_google_payloads():
    openai = {}
    apply_turn_mode_openai(openai, TurnMode.MANUAL)
    assert openai["session"]["turn_detection"] is None
    apply_turn_mode_openai(openai, TurnMode.AUTO)
    assert openai["session"]["turn_detection"] == {"type": "server_vad"}

    google = {}
    apply_turn_mode_google(google, TurnMode.MANUAL)
    assert google["realtime_input_config"]["automatic_activity_detection"]["disabled"] is True
    apply_turn_mode_google(google, TurnMode.AUTO)
    assert google["realtime_input_config"]["automatic_activity_detection"]["disabled"] is False


def test_set_session_handle_initializes_extra_and_persists():
    ctx = SimpleNamespace(extra=None)
    window = SimpleNamespace(core=SimpleNamespace(ctx=SimpleNamespace(update_item=MagicMock())))
    set_ctx_rt_handle(ctx, "  session-1  ", window)
    assert ctx.extra["rt_session_id"] == "session-1"
    window.core.ctx.update_item.assert_called_once_with(ctx)
    set_ctx_rt_handle(ctx, "   ", window)
    assert ctx.extra["rt_session_id"] == "session-1"
    set_ctx_rt_handle(None, "x", window)


def test_set_session_expiry_uses_epoch_timestamp_and_extracts_last_handle():
    ctx = SimpleNamespace(extra={})
    # Fixed epoch timestamp keeps the test independent from local timezone.
    epoch = 1_735_689_600
    set_rt_session_expires_at(ctx, epoch)
    assert ctx.extra["rt_session_expires_at"] == epoch
    set_rt_session_expires_at(ctx, None)
    assert extract_last_session_id([
        SimpleNamespace(extra={"rt_session_id": "old"}),
        None,
        SimpleNamespace(extra={"rt_session_id": "  newest  "}),
    ]) == "newest"
    assert extract_last_session_id([]) is None
    assert extract_last_session_id([SimpleNamespace(extra={"rt_session_id": " "})]) is None
