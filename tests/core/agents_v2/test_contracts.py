#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import FrozenInstanceError

import pytest

from pygpt_net.core.agents_v2.contracts import RuntimeInput, RuntimeOutput
from pygpt_net.core.agents_v2.mode import AgentMode


def test_runtime_input_keeps_high_level_dependencies_and_is_immutable():
    payload = RuntimeInput(
        window="window",
        context="context",
        extra={"x": 1},
        signals="signals",
        emitter="emitter",
    )

    assert payload.window == "window"
    assert payload.context == "context"
    assert payload.extra == {"x": 1}
    assert payload.signals == "signals"
    assert payload.emitter == "emitter"
    with pytest.raises(FrozenInstanceError):
        payload.window = "other"


def test_runtime_output_exposes_stable_execution_snapshot_and_is_immutable():
    output = RuntimeOutput(
        run_id="run-1",
        agent_mode=AgentMode.PRIMARY_AGENT,
        finished=True,
        final_answer="done",
    )

    assert output.run_id == "run-1"
    assert output.agent_mode is AgentMode.PRIMARY_AGENT
    assert output.finished is True
    assert output.final_answer == "done"
    with pytest.raises(FrozenInstanceError):
        output.finished = False
