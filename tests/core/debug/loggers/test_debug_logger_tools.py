from unittest.mock import MagicMock

from pygpt_net.core.debug.loggers.tools import ToolDebugLogger


def test_duplicate_cache_is_separate_for_calls_and_results():
    logger = ToolDebugLogger()
    assert logger._is_duplicate("call", "1", "tool") is False
    assert logger._is_duplicate("call", "1", "tool") is True
    assert logger._is_duplicate("result", "1", "tool") is False
    assert logger._is_duplicate("result", "1", "tool") is True
    assert logger._is_duplicate("call", None, "tool") is False
    assert logger._is_duplicate("call", "", "tool") is False


def test_duplicate_cache_evicts_oldest_entry(monkeypatch):
    logger = ToolDebugLogger()
    monkeypatch.setattr(logger, "_CACHE_LIMIT", 2)
    assert logger._is_duplicate("call", "1", "tool") is False
    assert logger._is_duplicate("call", "2", "tool") is False
    assert logger._is_duplicate("call", "3", "tool") is False
    assert logger._is_duplicate("call", "1", "tool") is False


def test_log_call_emits_once_for_same_call_id(monkeypatch):
    logger = ToolDebugLogger()
    monkeypatch.setattr(logger, "enabled", lambda key: True)
    logger.emit = MagicMock()

    logger.log_call("run", {"api_key": "secret"}, call_id=7, provider="p", actor="a", raw={"x": 1})
    logger.log_call("run", {"api_key": "secret"}, call_id=7, provider="p", actor="a")

    logger.emit.assert_called_once()
    title, payload = logger.emit.call_args.args
    assert title == "TOOL CALL"
    assert payload["call_id"] == "7"
    assert payload["params"]["api_key"] == "***MASKED***"
    assert payload["raw"] == {"x": 1}


def test_log_result_emits_error_and_extra(monkeypatch):
    logger = ToolDebugLogger()
    monkeypatch.setattr(logger, "enabled", lambda key: True)
    logger.emit = MagicMock()

    logger.log_result("run", {"ok": True}, call_id="c", error="err", extra={"n": 1})

    title, payload = logger.emit.call_args.args
    assert title == "TOOL RESULT"
    assert payload["response"] == {"ok": True}
    assert payload["error"] == "err"
    assert payload["extra"] == {"n": 1}
