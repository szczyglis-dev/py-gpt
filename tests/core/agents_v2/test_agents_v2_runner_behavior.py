#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pygpt_net.core.agents_v2.runner as runner_module
import pygpt_net.core.agents_v2.execution.events as events_module
from pygpt_net.core.agents_v2.agents import AgentsV2
from pygpt_net.core.agents_v2.runner import Runner


class FakeEmitter:
    instances = []

    def __init__(self, context, extra, signals):
        self.context = context
        self.extra = extra
        self.signals = signals
        self.finished = []
        self.clear_count = 0
        FakeEmitter.instances.append(self)

    def clear_status(self):
        self.clear_count += 1

    def finish(self, final_answer=None):
        self.finished.append(final_answer)


def test_agents_v2_wrapper_constructs_runner_with_same_window():
    window = object()
    agents = AgentsV2(window)

    assert agents.window is window
    assert agents.runner.window is window


def test_agents_v2_runner_call_success_returns_true_and_clears_previous_error(monkeypatch):
    runner = Runner(SimpleNamespace())
    runner.last_error = RuntimeError("old")
    runner.run_turn = AsyncMock(return_value=None)

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    assert result is True
    assert runner.get_error() is None
    runner.run_turn.assert_awaited_once()


def test_agents_v2_runner_call_treats_cancelled_error_as_normal_control_flow(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    runner = Runner(SimpleNamespace())
    runner.run_turn = AsyncMock(side_effect=asyncio.CancelledError())

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is True
    assert runner.get_error() is None
    assert emitter.clear_count == 1
    assert emitter.finished == [None]


def test_agents_v2_runner_call_logs_error_and_returns_false_for_bridge_error_path(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    window = MagicMock()
    runner = Runner(window)
    runner.run_turn = AsyncMock(side_effect=RuntimeError("boom"))

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is False
    assert isinstance(runner.get_error(), RuntimeError)
    window.core.debug.log.assert_called_once()
    assert emitter.clear_count == 1
    assert emitter.finished == [None]


@pytest.mark.parametrize("checkpoint", [False, True])
def test_agents_v2_runner_managed_final_stream_starts_before_first_final_delta(monkeypatch, checkpoint):
    class FakeAgentStream:
        def __init__(self, delta=""):
            self.delta = delta

    class FakeToolCall:
        pass

    class FakeToolCallResult:
        pass

    class FakeHandler:
        def __init__(self):
            self.cancel_run = AsyncMock()

        async def stream_events(self):
            if checkpoint:
                yield events_module.AgentCheckpoint()
            yield FakeToolCallResult()
            yield FakeAgentStream("final answer")

        def __await__(self):
            async def resolve():
                return SimpleNamespace(response=SimpleNamespace(content="final answer"))
            return resolve().__await__()

    handler = FakeHandler()
    llm = object()
    main_agent = SimpleNamespace(llm=llm, run=MagicMock(return_value=handler))
    runtime = SimpleNamespace(
        agent_mode=SimpleNamespace(value="orchestrator"),
        finished=False,
        final_answer="",
        shared_context_text="",
        uses_workflow_finish=True,
        main_max_iterations_configured=48,
        main_max_iterations=48,
        main_agent_name="Orchestrator",
        main_agent_description="desc",
        memory_store=SimpleNamespace(
            load_history=MagicMock(return_value=[]),
            begin_turn=MagicMock(return_value=SimpleNamespace(id=1)),
            complete_turn=MagicMock(),
        ),
        is_stopped=MagicMock(return_value=False),
        main_event=MagicMock(side_effect=lambda value: value),
        verbose=SimpleNamespace(text=MagicMock(), log=MagicMock()),
        inputs=SimpleNamespace(
            prefetch=MagicMock(),
            llm=MagicMock(return_value=llm),
            agent=MagicMock(return_value=main_agent),
            message=MagicMock(return_value="user message"),
        ),
        prompts=SimpleNamespace(main=MagicMock(return_value="system")),
        tools=SimpleNamespace(main=MagicMock(return_value=[])),
        artifacts=SimpleNamespace(collect_from_llm=MagicMock(), pending=MagicMock(return_value={})),
        tool_history=SimpleNamespace(export=MagicMock()),
        usage=SimpleNamespace(apply_to_context=MagicMock(return_value=(10, 5, 15))),
        workflow=SimpleNamespace(
            awaiting_final_response=True,
            final_requested=True,
            final_stream_started=False,
            final_hint="",
        ),
        timeline=SimpleNamespace(
            consume=MagicMock(),
            part_uuid=MagicMock(return_value="final-part"),
            final_output=MagicMock(return_value="final answer"),
            resolve_final=MagicMock(return_value="fallback"),
            mark_final=MagicMock(),
            memory_output=MagicMock(return_value="memory output"),
            part=MagicMock(return_value=SimpleNamespace(uuid="final-part")),
            last_output=MagicMock(return_value="final answer"),
            prepare_final=MagicMock(return_value=SimpleNamespace(uuid="final-part")),
            close_segment=MagicMock(),
            needs_new_part={},
        ),
        workers=SimpleNamespace(
            states={},
            cleanup=AsyncMock(),
            numbers={},
            parent_parts={},
            stored_context_runs=set(),
        ),
    )
    runtime.model = SimpleNamespace(id="model", provider="openai")
    runtime.window = SimpleNamespace(
        core=SimpleNamespace(
            context_manager=SimpleNamespace(enabled=MagicMock(return_value=False)),
            api=SimpleNamespace(
                logger=SimpleNamespace(log_input=MagicMock(), log_output=MagicMock()),
            ),
        ),
    )

    def begin_final_stream():
        runtime.workflow.final_stream_started = True
        return SimpleNamespace(uuid="final-part")

    runtime.timeline.begin_final_stream = MagicMock(side_effect=begin_final_stream)

    monkeypatch.setattr(runner_module, "AgentsV2Runtime", lambda *args, **kwargs: runtime)
    monkeypatch.setattr(events_module, "AgentStream", FakeAgentStream)
    monkeypatch.setattr(events_module, "ToolCall", FakeToolCall)
    monkeypatch.setattr(events_module, "ToolCallResult", FakeToolCallResult)

    emitter = MagicMock()
    emitter.append_streamed = AsyncMock()
    context = SimpleNamespace(
        ctx=SimpleNamespace(input="question"),
        prompt="question",
        preset=SimpleNamespace(),
        model=SimpleNamespace(),
    )

    asyncio.run(Runner(SimpleNamespace()).run_turn(context, {}, SimpleNamespace(), emitter))

    runtime.timeline.begin_final_stream.assert_called_once_with()
    assert emitter.mark_block_boundary.call_count == (2 if checkpoint else 1)
    assert runtime.timeline.close_segment.call_count == int(checkpoint)
    emitter.append_streamed.assert_awaited_once_with(
        "final answer",
        part_uuid="final-part",
        ensure_incremental=True,
    )
    assert runtime.final_answer == "final answer"
    runtime.timeline.mark_final.assert_called_once_with()
    emitter.accept_streamed_final.assert_called_once_with()
    emitter.stream_final.assert_not_called()
    runtime.workers.cleanup.assert_awaited_once_with()
    runtime.memory_store.begin_turn.assert_not_called()
    runtime.memory_store.complete_turn.assert_not_called()
    runtime.timeline.memory_output.assert_not_called()
