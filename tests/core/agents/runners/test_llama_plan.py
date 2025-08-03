#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.agents.runners.llama_plan import LlamaPlan

# Override translation to identity
@pytest.fixture(autouse=True)
def patch_trans(monkeypatch):
    monkeypatch.setattr("pygpt_net.core.agents.runners.llama_plan.trans", lambda key: key)

# Dummy context mimicking CtxItem
class DummyCtx:
    def __init__(self):
        self.input = ""
        self.output = ""
        self.cmds = []
        self.results = None
        self.extra = {}
    def set_input(self, txt):
        self.input = txt
    def set_output(self, txt):
        self.output = txt

# Fake step output for agent.run_step
class FakeStep:
    def __init__(self, is_last, output):
        self.is_last = is_last
        self.output = output

# Fake subtask for the plan
class FakeSubTask:
    def __init__(self, name, expected_output, dependencies):
        self.name = name
        self.expected_output = expected_output
        self.dependencies = dependencies

# Fake plan holding subtasks
class FakePlan:
    def __init__(self, sub_tasks):
        self.sub_tasks = sub_tasks

# Fake task returned by agent.state.get_task
class FakeTask:
    def __init__(self, task_id):
        self.task_id = task_id

# Fixture for a fake agent
@pytest.fixture
def fake_agent():
    agent = MagicMock()

    # Create a plan with one subtask
    sub_task = FakeSubTask("sub1", "expected", "deps")
    fake_plan = FakePlan([sub_task])
    plan_id = "plan1"
    agent.create_plan.return_value = plan_id
    agent.state.plan_dict = {plan_id: fake_plan}
    agent.state.get_task.return_value = FakeTask("task1")
    # run_step returns a non-final step then a final step.
    agent.run_step.side_effect = [FakeStep(False, "step1_output"), FakeStep(True, "step2_output")]
    agent.finalize_response.return_value = "final_response"
    return agent

# Fixture for a fake window with a dummy export_sources
@pytest.fixture
def fake_window():
    fake_win = MagicMock()
    fake_win.core.agents.tools.export_sources.side_effect = lambda output: [{"source": output}]
    return fake_win

@pytest.fixture
def fake_signals():
    return MagicMock(spec=BridgeSignals)

@pytest.fixture
def dummy_ctx():
    return DummyCtx()

# Create LlamaPlan instance and override methods from BaseRunner
@pytest.fixture
def llama_plan(fake_window):
    lp = LlamaPlan(window=fake_window)
    lp.is_stopped = MagicMock(return_value=False)
    lp.set_busy = MagicMock()
    lp.set_status = MagicMock()
    # Return a new dummy context every time
    lp.add_ctx = lambda ctx: DummyCtx()
    lp.send_response = MagicMock()
    return lp

def test_run_stopped(llama_plan, fake_agent, dummy_ctx, fake_signals):
    # Immediately return if stopped.
    llama_plan.is_stopped.return_value = True
    result = llama_plan.run(fake_agent, dummy_ctx, "prompt", fake_signals)
    assert result is True
    llama_plan.set_busy.assert_not_called()
    llama_plan.send_response.assert_not_called()

def test_run_normal(llama_plan, fake_agent, dummy_ctx, fake_signals):
    # Normal run should trigger sending of responses.
    result = llama_plan.run(fake_agent, dummy_ctx, "prompt", fake_signals, verbose=False)
    assert result is True
    # One response for plan, one for subtask step and one for final response.
    assert llama_plan.send_response.call_count == 3
    fake_agent.create_plan.assert_called_once()

def test_run_once_normal(llama_plan, fake_agent, dummy_ctx):
    # run_once should return a final context with final response.
    result_ctx = llama_plan.run_once(fake_agent, dummy_ctx, "prompt", verbose=False)
    assert result_ctx is not None
    assert result_ctx.output == "final_response"
    fake_agent.create_plan.assert_called_once()