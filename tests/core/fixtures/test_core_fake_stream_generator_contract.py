import asyncio
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.fixtures.stream.generator as mod
from pygpt_net.core.fixtures.stream.generator import FakeOpenAIStream, StreamConfig


FIXED_TS = 1_735_689_600


def test_start_and_prefix_normalizes_alias_and_clamps_rate(monkeypatch):
    stream = FakeOpenAIStream(rng_seed=7)
    monkeypatch.setattr(mod.time, "time", lambda: FIXED_TS)
    prefix, sleep_dt = stream._start_and_prefix(StreamConfig(api="respones", chunk="code", cps=999, min_newline=0))
    assert sleep_dt == pytest.approx(1 / 120)
    assert prefix == [{
        "type": "response.output_text.delta",
        "delta": "",
        "output_index": 0,
        "content_index": 0,
        "item_id": stream._msg_id,
    }]
    assert stream._run_id.startswith(f"chatcmpl_fake_{FIXED_TS}_")
    assert stream._code_mode is True


def test_start_and_prefix_rejects_unknown_api_and_chunk():
    stream = FakeOpenAIStream(rng_seed=1)
    with pytest.raises(ValueError, match="Unknown api"):
        stream._start_and_prefix(StreamConfig(api="bogus"))
    with pytest.raises(ValueError, match="Unknown chunk"):
        stream._start_and_prefix(StreamConfig(chunk="bogus"))


def test_chat_prefix_and_payload_use_epoch_timestamp(monkeypatch):
    stream = FakeOpenAIStream(rng_seed=3, model_name="model-x")
    monkeypatch.setattr(mod.time, "time", lambda: FIXED_TS)
    prefix, _ = stream._start_and_prefix(StreamConfig(api="chat", include_chat_role=True))
    assert len(prefix) == 1
    assert prefix[0]["created"] == FIXED_TS
    assert prefix[0]["model"] == "model-x"
    assert prefix[0]["choices"][0]["delta"] == {"role": "assistant", "content": ""}
    wrapped = stream._wrap_payload(StreamConfig(api="chat"), "abc")
    assert wrapped["created"] == FIXED_TS
    assert wrapped["choices"][0]["delta"] == {"content": "abc"}


def test_raw_and_responses_wrappers_are_provider_shaped():
    stream = FakeOpenAIStream(rng_seed=1)
    stream._msg_id = "msg_123"
    assert stream._wrap_payload(StreamConfig(api="raw"), "abc") == "abc"
    assert stream._wrap_payload(StreamConfig(api="responses"), "abc") == {
        "type": "response.output_text.delta",
        "delta": "abc",
        "output_index": 0,
        "content_index": 0,
        "item_id": "msg_123",
    }


def test_code_take_wraps_source_and_advances_position(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("abcd", encoding="utf-8")
    stream = FakeOpenAIStream(rng_seed=1, code_path=str(source))
    assert stream._code_take(6) == "abcdab"
    assert stream._code_pos == 2
    assert stream._code_take(3) == "cda"
    assert stream._code_pos == 1


def test_missing_code_file_falls_back_to_generated_code(tmp_path):
    stream = FakeOpenAIStream(rng_seed=1, code_path=str(tmp_path / "missing.py"))
    cfg = StreamConfig(chunk="code")
    piece = stream._make_piece(cfg)
    assert isinstance(piece, str)
    assert 5 <= len(piece) <= 28


def test_inject_newlines_is_deterministic_when_threshold_reached():
    stream = FakeOpenAIStream(rng_seed=1)
    stream._code_mode = False
    stream._chars_since_nl = 3
    stream._next_nl_at = 3
    result = stream._inject_newlines("abc", min_nl=10)
    assert result.startswith("\n")
    assert result.endswith("abc")


def test_sync_stream_stops_after_consumer_requests_stop(monkeypatch):
    stream = FakeOpenAIStream(rng_seed=9)
    monkeypatch.setattr(mod.time, "sleep", MagicMock())
    iterator = stream.stream(api="raw", cps=120)
    first = next(iterator)
    assert isinstance(first, str)
    stream.stop()
    with pytest.raises(StopIteration):
        next(iterator)


def test_async_stream_stops_without_real_sleep(monkeypatch):
    stream = FakeOpenAIStream(rng_seed=9)

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", no_sleep)

    async def consume():
        iterator = stream.astream(api="responses", cps=120)
        first = await anext(iterator)
        stream.stop()
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)
        return first

    first = asyncio.run(consume())
    assert first["type"] == "response.output_text.delta"
