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
from pygpt_net.core.agents.observer.evaluation import Evaluation

# Dummy context item for tests
class DummyCtxItem:
    def __init__(self, input_value="", output_value="", extra=None):
        self.input = input_value
        self.output = output_value
        self.extra = extra

@pytest.fixture
def dummy_window():
    class DummyLoop:
        def __init__(self):
            self.next_instruction = None
            self.prev_score = None

    class DummyRunner:
        def __init__(self):
            self.loop = DummyLoop()

    class DummyAgents:
        def __init__(self):
            self.runner = DummyRunner()

    class DummyCore:
        def __init__(self):
            self.config = {
                "agent.llama.append_eval": False,
                "prompt.agent.llama.eval":
                    "Task: {task}; Input: {input}; Output: {output}",
                "prompt.agent.llama.eval.complete":
                    "Complete - Task: {task}; Input: {input}; Output: {output}"
            }
            self.agents = DummyAgents()

    class DummyWindow:
        def __init__(self):
            self.core = DummyCore()

    return DummyWindow()

@pytest.fixture
def evaluation(dummy_window):
    return Evaluation(window=dummy_window)

def test_get_last_user_input_no_force(evaluation):
    # When append_eval is False, evaluation inputs should be skipped.
    history = [
        DummyCtxItem(input_value="First input", extra={"agent_input": True}),
        DummyCtxItem(input_value="Second input", extra={"agent_input": True, "agent_evaluate": True}),
    ]
    result = evaluation.get_last_user_input(history)
    assert result == "First input"

def test_get_last_user_input_force(evaluation):
    # With force_prev=True, evaluation inputs are not skipped.
    history = [
        DummyCtxItem(input_value="First input", extra={"agent_input": True}),
        DummyCtxItem(input_value="Second input", extra={"agent_input": True, "agent_evaluate": True}),
    ]
    result = evaluation.get_last_user_input(history, force_prev=True)
    assert result == "Second input"

def test_get_main_task(evaluation):
    history = [
        DummyCtxItem(input_value="Main task", extra={"agent_input": True}),
        DummyCtxItem(input_value="Another input", extra={"agent_input": True}),
    ]
    result = evaluation.get_main_task(history)
    assert result == "Main task"

def test_get_main_task_no_agent_input(evaluation):
    history = [DummyCtxItem(input_value="Ignored", extra={"other_key": True})]
    result = evaluation.get_main_task(history)
    assert result == ""

def test_get_final_response(evaluation):
    history = [
        DummyCtxItem(output_value="Intermediate", extra={"agent_finish": True}),
        DummyCtxItem(output_value="Final response", extra={"agent_finish": True}),
    ]
    result = evaluation.get_final_response(history)
    assert result == "Intermediate\n\nFinal response"

def test_get_prompt_score(evaluation):
    history = [
        DummyCtxItem(input_value="Task description", extra={"agent_input": True}),
        DummyCtxItem(input_value="User follow-up", extra={"agent_input": True}),
        DummyCtxItem(output_value="Agent final answer", extra={"agent_finish": True}),
    ]
    result = evaluation.get_prompt_score(history)
    expected = "Task: Task description; Input: User follow-up; Output: Agent final answer"
    assert result == expected

def test_get_prompt_complete(evaluation):
    history = [
        DummyCtxItem(input_value="Task description", extra={"agent_input": True}),
        DummyCtxItem(input_value="User follow-up", extra={"agent_input": True}),
        DummyCtxItem(output_value="Agent final answer", extra={"agent_finish": True}),
    ]
    result = evaluation.get_prompt_complete(history)
    expected = "Complete - Task: Task description; Input: User follow-up; Output: Agent final answer"
    assert result == expected

def test_get_tools(evaluation):
    tools = evaluation.get_tools()
    assert len(tools) == 1
    # Call the feedback function from the tool and verify evaluation update.
    feedback = tools[0].fn("Test instruction", 85)
    assert feedback == "OK. Feedback has been sent."
    core = evaluation.window.core
    assert core.agents.runner.loop.next_instruction == "Test instruction"
    assert core.agents.runner.loop.prev_score == 85

def test_handle_evaluation(evaluation):
    evaluation.handle_evaluation("New instruction", 90)
    core = evaluation.window.core
    assert core.agents.runner.loop.next_instruction == "New instruction"
    assert core.agents.runner.loop.prev_score == 90