#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.usage import RuntimeUsage


def make_runtime(ctx=None):
    verbose = MagicMock()
    return SimpleNamespace(
        verbose=verbose,
        context=SimpleNamespace(ctx=ctx),
    )


def test_get_first_and_as_int_support_dicts_objects_and_reject_invalid_values():
    obj = SimpleNamespace(value=2)

    assert RuntimeUsage._get({"value": 1}, "value") == 1
    assert RuntimeUsage._get(obj, "value") == 2
    assert RuntimeUsage._first({"b": 3}, ("a", "b")) == 3
    assert RuntimeUsage._as_int("4") == 4
    assert RuntimeUsage._as_int(-3) == 0
    assert RuntimeUsage._as_int(True) is None
    assert RuntimeUsage._as_int("bad") is None


def test_normalize_supports_openai_and_gemini_usage_and_preserves_reasoning_total():
    assert RuntimeUsage._normalize({"prompt_tokens": 10, "completion_tokens": 4}) == (10, 4, 14)
    assert RuntimeUsage._normalize({
        "promptTokenCount": 10,
        "candidatesTokenCount": 4,
        "totalTokenCount": 20,
    }) == (10, 10, 20)


def test_normalize_never_reports_total_lower_than_input_plus_output():
    assert RuntimeUsage._normalize({
        "input_tokens": 8,
        "output_tokens": 7,
        "total_tokens": 10,
    }) == (8, 7, 15)
    assert RuntimeUsage._normalize({"total_tokens": 0}) is None
    assert RuntimeUsage._normalize({"other": 1}) is None


def test_response_id_walks_common_wrappers_and_is_cycle_safe():
    raw = SimpleNamespace(response=SimpleNamespace(raw={"responseId": "resp-1"}))
    assert RuntimeUsage._response_id(raw) == "resp-1"

    cycle = {}
    cycle["raw"] = cycle
    assert RuntimeUsage._response_id(cycle) == ""


def test_usage_values_finds_nested_usage_without_infinite_wrapper_cycles():
    raw = {}
    raw["raw"] = raw
    raw["usage"] = {"input_tokens": 3, "output_tokens": 2}

    values = list(RuntimeUsage._usage_values(raw))

    assert any(RuntimeUsage._normalize(value) == (3, 2, 5) for value in values)


def test_capture_prefers_most_complete_nested_view_and_logs_turn_aggregate():
    runtime = make_runtime()
    usage = RuntimeUsage(runtime)
    response = {
        "id": "resp-1",
        "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13},
        "raw": {"usage_metadata": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}},
    }

    assert usage.capture(response, actor_id="worker-1") is True

    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.total_tokens == 15
    runtime.verbose.log.assert_called_once()
    assert runtime.verbose.log.call_args.kwargs["actor"] == "worker-1"


def test_capture_deduplicates_same_provider_response_for_same_actor():
    usage = RuntimeUsage(make_runtime())
    response = {"id": "resp-1", "usage": {"input_tokens": 2, "output_tokens": 1}}

    assert usage.capture(response, actor_id="orchestrator") is True
    assert usage.capture(response, actor_id="orchestrator") is False
    assert usage.total_tokens == 3


def test_capture_counts_same_response_id_for_different_actors_independently():
    usage = RuntimeUsage(make_runtime())
    response = {"id": "resp-1", "usage": {"input_tokens": 2, "output_tokens": 1}}

    assert usage.capture(response, actor_id="a") is True
    assert usage.capture(response, actor_id="b") is True
    assert usage.total_tokens == 6


def test_capture_without_response_id_uses_root_identity_and_keeps_root_alive():
    usage = RuntimeUsage(make_runtime())
    response = {"usage": {"input_tokens": 4, "output_tokens": 2}}

    assert usage.capture(response) is True
    assert usage.capture(response) is False
    assert usage._seen_roots == [response]


def test_capture_returns_false_when_usage_is_missing():
    usage = RuntimeUsage(make_runtime())

    assert usage.capture({"id": "resp"}) is False
    assert usage.total_tokens == 0


def test_capture_ignores_verbose_logging_failure():
    runtime = make_runtime()
    runtime.verbose.log.side_effect = RuntimeError("logger")
    usage = RuntimeUsage(runtime)

    assert usage.capture({"usage": {"input_tokens": 1, "output_tokens": 1}}) is True
    assert usage.total_tokens == 2


def test_apply_to_context_uses_set_tokens_when_available():
    ctx = SimpleNamespace(set_tokens=MagicMock())
    usage = RuntimeUsage(make_runtime(ctx))
    usage.input_tokens = 11
    usage.output_tokens = 7

    assert usage.apply_to_context() == (11, 7, 18)
    ctx.set_tokens.assert_called_once_with(11, 7)


def test_apply_to_context_falls_back_to_plain_attributes_and_supports_missing_ctx():
    ctx = SimpleNamespace()
    usage = RuntimeUsage(make_runtime(ctx))
    usage.input_tokens = 5
    usage.output_tokens = 3

    assert usage.apply_to_context() == (5, 3, 8)
    assert (ctx.input_tokens, ctx.output_tokens, ctx.total_tokens) == (5, 3, 8)

    usage.runtime.context.ctx = None
    assert usage.apply_to_context() == (5, 3, 8)
