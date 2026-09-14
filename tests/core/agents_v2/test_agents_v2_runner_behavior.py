#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pygpt_net.core.agents_v2.runner as runner_module
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
    runner._run = AsyncMock(return_value=None)

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    assert result is True
    assert runner.get_error() is None
    runner._run.assert_awaited_once()


def test_agents_v2_runner_call_treats_cancelled_error_as_normal_control_flow(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    runner = Runner(SimpleNamespace())
    runner._run = AsyncMock(side_effect=asyncio.CancelledError())

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is True
    assert runner.get_error() is None
    assert emitter.clear_count == 1
    assert emitter.finished == [None]


def test_agents_v2_runner_call_logs_error_and_finishes_visible_response(monkeypatch):
    FakeEmitter.instances.clear()
    monkeypatch.setattr(runner_module, "RuntimeEmitter", FakeEmitter)
    window = MagicMock()
    runner = Runner(window)
    runner._run = AsyncMock(side_effect=RuntimeError("boom"))

    result = runner.call(SimpleNamespace(), {}, SimpleNamespace())

    emitter = FakeEmitter.instances[-1]
    assert result is True
    assert isinstance(runner.get_error(), RuntimeError)
    window.core.debug.log.assert_called_once()
    assert emitter.clear_count == 1
    assert emitter.finished == ["Chat with Agents: boom"]


def test_agents_v2_runner_managed_final_stream_starts_before_first_final_delta(monkeypatch):
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
        workers={},
        uses_workflow_finish=True,
        main_max_iterations_configured=48,
        main_max_iterations=48,
        workflow_final_requested=True,
        workflow_final_stream_started=False,
        workflow_final_hint="",
        awaiting_workflow_final_response=True,
        main_agent_name="Orchestrator",
        main_agent_description="desc",
        memory_store=SimpleNamespace(
            load_history=MagicMock(return_value=[]),
            begin_turn=MagicMock(return_value=SimpleNamespace(id=1)),
            complete_turn=MagicMock(),
        ),
        verbose_text=MagicMock(),
        verbose_log=MagicMock(),
        prefetch_rag_context=MagicMock(),
        get_llm=MagicMock(return_value=llm),
        build_agent=MagicMock(return_value=main_agent),
        main_agent_prompt=MagicMock(return_value="system"),
        main_agent_tools=MagicMock(return_value=[]),
        build_user_message=MagicMock(return_value="user message"),
        is_stopped=MagicMock(return_value=False),
        verbose_event=MagicMock(),
        actor_part_uuid=MagicMock(return_value="final-part"),
        collect_llm_artifacts=MagicMock(),
        primary_stream_final_output=MagicMock(return_value="final answer"),
        resolve_primary_final_output=MagicMock(return_value="fallback"),
        mark_current_part_final=MagicMock(),
        orchestrator_memory_output=MagicMock(return_value="memory output"),
        cleanup=AsyncMock(),
        export_tool_calls_to_main_ctx=MagicMock(),
        _actor_part=MagicMock(return_value=SimpleNamespace(uuid="final-part")),
        main_event=MagicMock(side_effect=lambda value: value),
        last_orchestrator_output=MagicMock(return_value="final answer"),
        _prepare_final_part=MagicMock(return_value=SimpleNamespace(uuid="final-part")),
        _swarm_worker_numbers={},
        _worker_parent_parts={},
        _stored_worker_context_runs=set(),
    )
    runtime.model = SimpleNamespace(id="model", provider="openai")
    runtime.window = SimpleNamespace(
        core=SimpleNamespace(
            context_manager=SimpleNamespace(enabled=MagicMock(return_value=False)),
            api=SimpleNamespace(
                logger=SimpleNamespace(log_input=MagicMock(), log_output=MagicMock())
            ),
        )
    )

    def begin_final_stream():
        runtime.workflow_final_stream_started = True
        return SimpleNamespace(uuid="final-part")

    runtime.begin_workflow_final_stream = MagicMock(side_effect=begin_final_stream)

    monkeypatch.setattr(runner_module, "AgentsV2Runtime", lambda *args, **kwargs: runtime)
    monkeypatch.setattr(runner_module, "AgentStream", FakeAgentStream)
    monkeypatch.setattr(runner_module, "ToolCall", FakeToolCall)
    monkeypatch.setattr(runner_module, "ToolCallResult", FakeToolCallResult)

    emitter = MagicMock()
    emitter.append_streamed = AsyncMock()
    context = SimpleNamespace(
        ctx=SimpleNamespace(input="question"),
        prompt="question",
        preset=SimpleNamespace(),
        model=SimpleNamespace(),
    )

    asyncio.run(Runner(SimpleNamespace())._run(context, {}, SimpleNamespace(), emitter))

    runtime.begin_workflow_final_stream.assert_called_once_with()
    emitter.mark_block_boundary.assert_called_once_with()
    emitter.append_streamed.assert_awaited_once_with(
        "final answer",
        part_uuid="final-part",
        ensure_incremental=True,
    )
    assert runtime.final_answer == "final answer"
    runtime.mark_current_part_final.assert_called_once_with()
    emitter.accept_streamed_final.assert_called_once_with()
    emitter.stream_final.assert_not_called()
    runtime.cleanup.assert_awaited_once_with()
