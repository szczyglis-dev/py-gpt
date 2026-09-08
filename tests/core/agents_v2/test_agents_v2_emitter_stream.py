#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import asyncio

from pygpt_net.core.agents_v2.emitter import RuntimeEmitter
from pygpt_net.core.agents_v2.tool_bridge import get as get_tool_request
from pygpt_net.core.events import KernelEvent


def make_emitter():
    signals = SimpleNamespace(response=MagicMock())
    emitter = RuntimeEmitter(context="ctx", extra={"x": 1}, signals=signals)
    emitter._stream_emit_chars = 1
    return emitter, signals


def emitted_events(signals):
    return [call.args[0] for call in signals.response.emit.call_args_list]


def test_agents_v2_emitter_begin_is_idempotent():
    emitter, signals = make_emitter()

    emitter.begin()
    emitter.begin()

    events = emitted_events(signals)
    assert [event.name for event in events] == [KernelEvent.AGENT_V2_BEGIN]
    assert events[0].data["context"] == "ctx"
    assert events[0].data["extra"] == {"x": 1}


def test_agents_v2_emitter_append_streams_and_inserts_block_boundary():
    emitter, signals = make_emitter()

    emitter.append("first")
    emitter.mark_block_boundary()
    emitter.append("second")

    append_events = [e for e in emitted_events(signals) if e.name == KernelEvent.AGENT_V2_APPEND]
    assert emitter.text == "firstsecond"
    assert append_events[0].data["chunk"] == "first"
    assert append_events[0].data["begin"] is True
    assert append_events[1].data["chunk"] == "second"
    assert append_events[1].data["begin"] is False


def test_agents_v2_emitter_status_flushes_stream_and_deduplicates_value():
    emitter, signals = make_emitter()

    emitter.append("text")
    emitter.status("working", source="w01")
    emitter.status("working", source="w01")
    emitter.clear_status()

    status_events = [e for e in emitted_events(signals) if e.name == KernelEvent.AGENT_V2_STATUS]
    assert [(e.data["status"], e.data["source"]) for e in status_events] == [
        ("working", "w01"),
        ("", "orchestrator"),
    ]


def test_agents_v2_emitter_finish_does_not_duplicate_already_streamed_final_answer():
    emitter, signals = make_emitter()
    emitter.append("final answer")
    before = len([e for e in emitted_events(signals) if e.name == KernelEvent.AGENT_V2_APPEND])

    emitter.finish("final answer")
    emitter.finish("ignored")

    events = emitted_events(signals)
    after = len([e for e in events if e.name == KernelEvent.AGENT_V2_APPEND])
    end_events = [e for e in events if e.name == KernelEvent.AGENT_V2_END]
    # finish() starts an authoritative final segment, replacing the working draft.
    assert after == before + 1
    final_begin = [e for e in events if e.name == KernelEvent.AGENT_V2_FINAL_BEGIN]
    assert len(final_begin) == 1
    assert emitter.text == "final answer"
    assert len(end_events) == 1
    assert end_events[0].data["final_answer"] == "final answer"


def test_agents_v2_emitter_execute_plugin_pairs_request_and_cleans_bridge():
    emitter, signals = make_emitter()
    tool_ctx = object()

    def complete_tool(event):
        if event.name != KernelEvent.AGENT_V2_TOOL_EXEC:
            return
        request = event.data["request"]
        assert get_tool_request(tool_ctx) is request
        request["result"] = {"ok": True}
        request["done"].set()

    signals.response.emit.side_effect = complete_tool

    result = asyncio.run(emitter.execute_plugin(tool_ctx, [{"cmd": "demo", "params": {}}], lambda: False))

    assert result == {"ok": True}
    assert get_tool_request(tool_ctx) is None


def test_agents_v2_emitter_execute_plugin_returns_cancelled_when_stop_is_requested():
    emitter, _signals = make_emitter()
    tool_ctx = object()

    result = asyncio.run(emitter.execute_plugin(tool_ctx, [], lambda: True))

    assert result == "Execution cancelled."
    assert get_tool_request(tool_ctx) is None
