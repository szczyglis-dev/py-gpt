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


def test_durable_part_lifecycle_and_private_worker_prose():
    from pygpt_net.core.ctx import Ctx
    from pygpt_net.item.ctx import CtxItem
    runtime = make_runtime()
    runtime.window = MagicMock()
    runtime.window.core.ctx = Ctx(runtime.window)
    runtime.window.core.ctx.provider = MagicMock()
    main = CtxItem('agent_v2')
    main.id = 1
    runtime.context.ctx = main
    runtime.main_agent_name = 'Primary'
    runtime.tool_history = MagicMock()
    runtime.workers.parent_parts = {}
    runtime.artifacts = MagicMock()
    runtime.verbose = MagicMock()
    timeline = runtime.timeline
    first = timeline.begin_part('orchestrator')
    assert first.name == 'Primary' and timeline.part_uuid() == first.uuid
    runtime.workers.parent_parts['w'] = first
    runtime.workers.states['w'] = SimpleNamespace(id='w', name='Writer', current_task='write')
    assert timeline.metadata('w') == ('w', 'Writer', 'write')
    assert timeline.part('w') is first
    assert timeline.begin_part('w') is first
    assert timeline.prepare_response('w') is None
    timeline.note_tool_activity('read', actor='w')
    assert timeline.has_tool_activity('w')
    timeline.reset_tool_activity('w')
    assert not timeline.has_tool_activity('w')
    first.set_output('progress\n\nfinal')
    assert timeline.last_output() == 'progress\n\nfinal'
    assert timeline.detach_final_suffix('final') is True
    assert first.output == 'progress'
    timeline.needs_new_part['orchestrator'] = True
    assert timeline.boundary_pending()
    second = timeline.prepare_response('orchestrator')
    assert second is not first and not timeline.boundary_pending()
    assert timeline.part_uuid(prepare_response=True) == second.uuid
    timeline.mark_final()
    assert second.extra['agents_v2_final'] is True
    second.set_output('answer')
    final = timeline.prepare_final()
    assert final is not second and final.extra['agents_v2_final'] is True
    runtime.memory_store = MagicMock()
    runtime.final_answer = 'final'
    assert timeline.memory_output() is runtime.memory_store.compose_turn_output.return_value
    runtime.memory_store.compose_turn_output.assert_called_once_with(main, final_answer='final')


def test_consuming_provider_events_records_calls_and_rotates_only_for_prose():
    from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult
    from llama_index.core.tools import ToolOutput
    runtime = make_runtime()
    runtime.artifacts = MagicMock()
    runtime.verbose = MagicMock()
    runtime.tool_history = MagicMock()
    timeline = runtime.timeline
    timeline.prepare_response = MagicMock()
    call = ToolCall(tool_id='call', tool_name='read', tool_kwargs={})
    timeline.stream_current = 'progress'
    timeline.consume(call)
    assert timeline.stream_completed == ['progress']
    runtime.tool_history.record_call.assert_called_once_with(call, actor='orchestrator')
    result = ToolCallResult(tool_id='call', tool_name='read', tool_kwargs={},
                           tool_output=ToolOutput(content='result', tool_name='read', raw_input={}, raw_output='result'),
                           return_direct=False)
    timeline.consume(result)
    assert timeline.boundary_pending()
    runtime.tool_history.record_result.assert_called_once_with(result, actor='orchestrator')
    timeline.consume(AgentStream(delta='', response='', current_agent_name='Primary', tool_calls=[], raw={}))
    timeline.prepare_response.assert_not_called()
    timeline.consume(AgentStream(delta='answer', response='answer', current_agent_name='Primary', tool_calls=[], raw={}))
    timeline.prepare_response.assert_called_once_with('orchestrator')
    assert timeline.final_output() == 'answer'
