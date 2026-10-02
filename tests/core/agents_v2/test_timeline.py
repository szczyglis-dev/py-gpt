#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.timeline import RuntimeTimeline


def make_runtime(parts=None):
    runtime = SimpleNamespace(
        context=SimpleNamespace(ctx=SimpleNamespace(parts=list(parts or []))),
        emitter=SimpleNamespace(mark_block_boundary=MagicMock()),
        verbose=SimpleNamespace(log=MagicMock()),
        status=SimpleNamespace(
            show_tool=MagicMock(return_value=False),
            emit=MagicMock(),
            worker=MagicMock(),
        ),
        workers=SimpleNamespace(states={}),
    )
    runtime.timeline = RuntimeTimeline(runtime)
    return runtime


def part(output, agent_id="orchestrator", extra=None):
    return SimpleNamespace(output=output, agent_id=agent_id, extra={} if extra is None else extra)


def test_provider_tool_activity_closes_primary_segment_and_arms_next_partial():
    runtime = make_runtime()
    runtime.timeline.stream_current = "progress before tool"
    timeline = runtime.timeline

    timeline.note_tool_activity("web_search", call_id="call-1")

    assert runtime.timeline.primary_tool_activity_seen is True
    assert runtime.timeline.stream_completed == ["progress before tool"]
    assert runtime.timeline.stream_current == ""
    assert runtime.timeline.needs_new_part["orchestrator"] is True
    runtime.emitter.mark_block_boundary.assert_called_once_with()


def test_primary_prose_outputs_ignore_worker_and_non_provider_history_rows():
    runtime = make_runtime([
        part("first"),
        part("worker", agent_id="w01"),
        part("hidden", extra={"provider_history": False}),
        part("second"),
    ])
    timeline = runtime.timeline

    assert timeline._prose_outputs() == ["first", "second"]


def test_strip_primary_prose_prefix_removes_only_exact_chronological_prefixes():
    runtime = make_runtime([part("planning"), part("checked data")])
    timeline = runtime.timeline

    assert timeline._strip_prose_prefix(
        "planning\n\nchecked data\n\nfinal answer"
    ) == "final answer"
    assert timeline._strip_prose_prefix("different final") == "different final"
    assert timeline._strip_prose_prefix("planning") == "planning"


def test_resolve_primary_final_output_prefers_current_stream_after_last_tool_boundary():
    runtime = make_runtime([part("persisted fallback")])
    runtime.timeline.stream_current = " final streamed "
    timeline = runtime.timeline
    runtime.timeline._strip_prose_prefix = timeline._strip_prose_prefix

    assert timeline.resolve_final("terminal aggregate") == "final streamed"
