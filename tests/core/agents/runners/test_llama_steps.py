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
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.agents.runners.llama_steps import LlamaSteps


# Dummy classes for window and context
class DummyTools:
    def export_sources(self, output):
        return [output]

class DummyAgents:
    def __init__(self):
        self.tools = DummyTools()

class DummyCore:
    def __init__(self):
        self.agents = DummyAgents()

class DummyWindow:
    def __init__(self):
        self.core = DummyCore()

class DummyCtx:
    def __init__(self):
        self.input = ""
        self.output = ""
        self.cmds = None
        self.results = []
        self.extra = {}

    def set_input(self, value):
        self.input = value

    def set_output(self, value):
        self.output = value


# Test run() returns immediately when stopped
def test_run_stopped():
    window = DummyWindow()
    runner = LlamaSteps(window)
    runner.is_stopped = MagicMock(return_value=True)
    dummy_agent = MagicMock()
    ctx = DummyCtx()
    signals = MagicMock()

    result = runner.run(dummy_agent, ctx, "prompt", signals, verbose=False)
    assert result is True
    dummy_agent.create_task.assert_not_called()


# Test normal run execution
def test_run_normal():
    window = DummyWindow()
    runner = LlamaSteps(window)
    runner.is_stopped = MagicMock(return_value=False)
    runner.prepare_input = lambda prompt: prompt
    runner.set_busy = MagicMock()
    runner.set_idle = MagicMock()
    runner.send_response = MagicMock()
    runner.add_ctx = lambda ctx: DummyCtx()

    dummy_agent = MagicMock()
    dummy_task = MagicMock()
    dummy_task.task_id = "task-1"
    dummy_agent.create_task.return_value = dummy_task

    step1 = MagicMock()
    step1.is_last = False
    step1.output = "step1_output"

    step2 = MagicMock()
    step2.is_last = True
    step2.output = "step2_output"

    dummy_agent.run_step.side_effect = [step1, step2]
    dummy_agent.finalize_response.return_value = "final_response"

    ctx = DummyCtx()
    signals = MagicMock()
    result = runner.run(dummy_agent, ctx, "prompt text", signals, verbose=True)
    assert result is True
    dummy_agent.create_task.assert_called_once_with("prompt text")
    assert dummy_agent.run_step.call_count == 2
    dummy_agent.finalize_response.assert_called_once_with("task-1")

    # Check that send_response is called with KernelEvent.APPEND_DATA in both steps
    for args, _ in runner.send_response.call_args_list:
        assert args[2] == KernelEvent.APPEND_DATA

    runner.set_idle.assert_called_once_with(signals)


# Test run_once() returns None when stopped
def test_run_once_stopped():
    window = DummyWindow()
    runner = LlamaSteps(window)
    runner.is_stopped = MagicMock(return_value=True)
    dummy_agent = MagicMock()
    ctx = DummyCtx()

    result = runner.run_once(dummy_agent, ctx, "prompt", verbose=False)
    assert result is None
    dummy_agent.create_task.assert_not_called()


# Test normal run_once() execution
def test_run_once_normal():
    window = DummyWindow()
    runner = LlamaSteps(window)
    runner.is_stopped = MagicMock(return_value=False)
    runner.prepare_input = lambda prompt: prompt
    runner.add_ctx = lambda ctx: DummyCtx()

    dummy_agent = MagicMock()
    dummy_task = MagicMock()
    dummy_task.task_id = "task-1"
    dummy_agent.create_task.return_value = dummy_task

    final_step = MagicMock()
    final_step.is_last = True
    final_step.output = "final_output"
    dummy_agent.run_step.return_value = final_step
    dummy_agent.finalize_response.return_value = "final_response"

    ctx = DummyCtx()
    result = runner.run_once(dummy_agent, ctx, "prompt text", verbose=True)
    assert result is not None
    assert result.input == str(["final_output"])
    assert result.output == "final_response"
    assert result.extra.get("agent_output") is True
    assert result.extra.get("agent_finish") is True
    dummy_agent.create_task.assert_called_once_with("prompt text")
    dummy_agent.run_step.assert_called_once_with("task-1")
    dummy_agent.finalize_response.assert_called_once_with("task-1")