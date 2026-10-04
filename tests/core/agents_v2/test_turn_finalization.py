import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.execution.finalization import TurnFinalization


def test_finalization_captures_state_and_artifacts_before_cleanup_then_commits_turn():
    order = []
    original_llm, agent_llm = object(), object()
    runtime = SimpleNamespace(
        window=MagicMock(),
        model=SimpleNamespace(id="model", provider="provider"),
        agent_mode=SimpleNamespace(value="orchestrator"),
        finished=True,
        final_answer="answer",
        is_stopped=lambda: False,
        timeline=SimpleNamespace(
            last_output=lambda: "answer",
            part=lambda *args, **kwargs: SimpleNamespace(uuid="final-part"),
        ),
        verbose=SimpleNamespace(log=MagicMock()),
        artifacts=SimpleNamespace(
            collect_from_llm=lambda llm, **kwargs: order.append(("artifacts", llm)),
            pending=lambda: {"files": ["report.txt"]},
        ),
        tool_history=SimpleNamespace(export=lambda: order.append("export")),
        workers=SimpleNamespace(
            states={},
            numbers={"w1": 1},
            parent_parts={"w1": SimpleNamespace(uuid="launch-part")},
            stored_context_runs={"w1:1"},
        ),
    )

    async def cleanup():
        order.append("cleanup")
        runtime.workers.numbers.clear()
        runtime.workers.parent_parts.clear()
        runtime.workers.stored_context_runs.clear()

    def usage():
        order.append("usage")
        return 10, 20, 30

    runtime.usage = SimpleNamespace()
    runtime.workers.cleanup, runtime.usage.apply_to_context = cleanup, usage
    emitter = SimpleNamespace(
        clear_status=lambda: order.append("clear"),
        finish=MagicMock(side_effect=lambda *args, **kwargs: order.append("finish")),
    )
    prepared = SimpleNamespace(agent=SimpleNamespace(llm=agent_llm), llm=original_llm)
    asyncio.run(TurnFinalization(runtime, emitter).finish(prepared, SimpleNamespace(count=3, types={"AgentStream": 3}), None))
    assert order == [("artifacts", agent_llm), ("artifacts", original_llm), "cleanup", "export", "usage", "clear", "finish"]
    assert runtime.debug_cleanup_snapshot["swarm_worker_numbers"] == {"w1": 1}
    assert runtime.debug_cleanup_snapshot["worker_parent_parts"] == {"w1": "launch-part"}
    assert runtime.debug_cleanup_snapshot["stored_worker_context_runs"] == ["w1:1"]
    emitter.finish.assert_called_once_with("answer", part_uuid="final-part", artifacts={"files": ["report.txt"]})
    assert runtime.window.core.api.logger.log_output.call_args.kwargs["chunks"] == 3
