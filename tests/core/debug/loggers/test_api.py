from unittest.mock import MagicMock

from pygpt_net.core.debug.loggers.api import ApiDebugLogger


def test_log_input_emits_sanitized_payload(monkeypatch):
    logger = ApiDebugLogger()
    monkeypatch.setattr(logger, "enabled", lambda key: True)
    logger.emit = MagicMock()

    logger.log_input(
        type="chat",
        provider="openai",
        kwargs={"api_key": "secret", "temperature": 1},
        input="hello",
        model="m",
    )

    title, payload = logger.emit.call_args.args
    assert title == "API INPUT"
    assert payload["type"] == "chat"
    assert payload["provider"] == "openai"
    assert payload["kwargs"]["api_key"] == "***MASKED***"
    assert payload["input"] == "hello"


def test_log_input_does_nothing_when_disabled(monkeypatch):
    logger = ApiDebugLogger()
    monkeypatch.setattr(logger, "enabled", lambda key: False)
    logger.emit = MagicMock()
    logger.log_input(type="chat")
    logger.emit.assert_not_called()


def test_summary_describes_strings_lists_and_dicts():
    logger = ApiDebugLogger()
    assert logger._summary("abc") == {"type": "str", "length": 3, "preview": "abc"}

    listed = logger._summary([{"type": "tool"}, {"role": "assistant"}])
    assert listed["count"] == 2
    assert listed["item_types"] == {"tool": 1, "assistant": 1}

    mapped = logger._summary({"id": "r1", "output": ["a", "b"], "ignored": 3})
    assert mapped["id"] == "r1"
    assert mapped["keys"] == ["id", "output", "ignored"]
    assert mapped["output"]["count"] == 2


def test_log_output_emits_summary_and_metadata(monkeypatch):
    logger = ApiDebugLogger()
    monkeypatch.setattr(logger, "enabled", lambda key: True)
    logger.emit = MagicMock()

    logger.log_output(
        type="responses",
        provider="openai",
        output="answer",
        chunks=2,
        chunk_types={"text": 2},
        usage={"input_tokens": 3},
        error="oops",
    )

    title, payload = logger.emit.call_args.args
    assert title == "API OUTPUT"
    assert payload["chunks"] == 2
    assert payload["chunk_types"] == {"text": 2}
    assert payload["summary"]["preview"] == "answer"
    assert payload["usage"] == {"input_tokens": 3}
    assert payload["error"] == "oops"
