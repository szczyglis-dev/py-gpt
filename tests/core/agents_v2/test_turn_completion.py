import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pygpt_net.core.agents_v2.execution.completion import TurnCompletion


@pytest.mark.parametrize("scenario,expected,accepted", [
    ("limit", "Iteration limit reached; task may be incomplete.\n\nanswer", False),
    ("stalled", "Agent repeated an unchanged checkpoint; task may be incomplete.\n\nanswer", False),
    ("managed_stream", "streamed answer", True),
    ("managed_fallback", "answer", False),
    ("managed_hint", "legacy hint", False),
    ("managed_missing_finish", "answer", True),
    ("primary_stream", "answer", True),
    ("primary_replay", "answer", False),
])
def test_terminal_answer_policy_never_duplicates_an_already_streamed_answer(scenario, expected, accepted):
    managed = scenario.startswith("managed")
    fallback = "" if scenario == "managed_hint" else "answer"
    runtime = SimpleNamespace(
        finished=False,
        final_answer="",
        uses_workflow_finish=managed,
        is_stopped=lambda: False,
        main_event=lambda name: name,
        artifacts=SimpleNamespace(collect_from_llm=MagicMock()),
        verbose=SimpleNamespace(text=MagicMock()),
        timeline=SimpleNamespace(
            final_output=lambda: "streamed answer" if scenario == "managed_stream" else "",
            resolve_final=lambda text: text,
            last_output=lambda: "answer" if scenario in {"primary_stream", "managed_missing_finish"} else "",
            detach_final_suffix=MagicMock(),
            mark_final=MagicMock(),
            prepare_final=MagicMock(return_value=SimpleNamespace(uuid="final-part")),
        ),
        workflow=SimpleNamespace(
            final_requested=scenario != "managed_missing_finish",
            final_stream_started=scenario == "managed_stream",
            final_hint="legacy hint",
        ),
    )
    agent = SimpleNamespace(
        llm=object(),
        iteration_limit_reached=scenario == "limit",
        stalled=scenario == "stalled",
    )
    emitter = SimpleNamespace(accept_streamed_final=MagicMock(), stream_final=AsyncMock())

    async def terminal():
        return fallback

    asyncio.run(TurnCompletion(runtime, emitter).complete(terminal(), SimpleNamespace(agent=agent, llm=agent.llm)))
    assert runtime.finished
    assert runtime.final_answer == expected
    assert emitter.accept_streamed_final.call_count == int(accepted)
    assert emitter.stream_final.await_count == int(not accepted)
    if not accepted:
        emitter.stream_final.assert_awaited_once_with(expected, part_uuid="final-part")
    if not managed and scenario.startswith("primary"):
        runtime.timeline.detach_final_suffix.assert_called_once_with(expected)
