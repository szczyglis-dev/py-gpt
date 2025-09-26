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

from pygpt_net.core.agents.runners.openai_workflow import OpenAIWorkflow


# Dummy class to simulate CtxItem behavior
class DummyCtx:
    def __init__(self):
        self.extra = {}
        self.input = None
        self.output = None
        self.agent_final_response_val = None
        self.msg_id = None

    def set_input(self, text):
        self.input = text

    def set_output(self, text):
        self.output = text

    def set_agent_final_response(self, text):
        self.agent_final_response_val = text

    def set_agent_name(self, name):
        pass

    def get_agent_name(self):
        return "DummyAgent"


@pytest.fixture
def dummy_window():
    # Create a dummy window with a mocked core.agents.tools
    dummy_tools = MagicMock()
    dummy_agents = MagicMock()
    dummy_agents.tools = dummy_tools
    dummy_core = MagicMock()
    dummy_core.agents = dummy_agents
    dummy_win = MagicMock()
    dummy_win.core = dummy_core
    return dummy_win


@pytest.fixture
def workflow(dummy_window):
    # Create an instance of OpenAIWorkflow with the dummy window.
    return OpenAIWorkflow(window=dummy_window)


def test_make_response_with_tool_outputs(monkeypatch, workflow):
    # Prepare a dummy response context and patch add_ctx to return it.
    dummy_response_ctx = DummyCtx()
    monkeypatch.setattr(workflow, "add_ctx", lambda ctx, with_tool_outputs: dummy_response_ctx)

    # Create a dummy context with non-empty agent_final_response and True use_agent_final_response.
    dummy_ctx = DummyCtx()
    dummy_ctx.agent_final_response = "existing final response"
    dummy_ctx.use_agent_final_response = True

    input_text = "input text"
    output_text = "output text"
    response_id = "resp-123"

    result = workflow.make_response(dummy_ctx, input_text, output_text, response_id)

    # Assertions for response context modifications.
    assert dummy_response_ctx.input == input_text
    assert dummy_response_ctx.output == output_text
    assert dummy_response_ctx.agent_final_response_val == output_text
    assert dummy_response_ctx.msg_id == response_id
    assert dummy_response_ctx.extra.get("agent_output") is True
    assert dummy_response_ctx.extra.get("agent_finish") is True
    # Extra 'output' key is set from the original context.
    assert dummy_response_ctx.extra.get("output") == "existing final response"

    # Verify that the append method was called and extract was not.
    workflow.window.core.agents.tools.append_tool_outputs.assert_called_once_with(dummy_response_ctx)
    workflow.window.core.agents.tools.extract_tool_outputs.assert_not_called()


def test_make_response_without_tool_outputs(monkeypatch, workflow):
    # Prepare a dummy response context and patch add_ctx.
    dummy_response_ctx = DummyCtx()
    monkeypatch.setattr(workflow, "add_ctx", lambda ctx, with_tool_outputs: dummy_response_ctx)

    # Create a dummy context with an empty agent_final_response and False use_agent_final_response.
    dummy_ctx = DummyCtx()
    dummy_ctx.agent_final_response = ""  # empty evaluates to False
    dummy_ctx.use_agent_final_response = False

    input_text = "input data"
    output_text = "output data"
    response_id = "resp-456"

    result = workflow.make_response(dummy_ctx, input_text, output_text, response_id)

    # Assertions for modifications.
    assert dummy_response_ctx.input == input_text
    assert dummy_response_ctx.output == output_text
    assert dummy_response_ctx.agent_final_response_val == output_text
    assert dummy_response_ctx.msg_id == response_id
    assert dummy_response_ctx.extra.get("agent_output") is True
    assert dummy_response_ctx.extra.get("agent_finish") is True
    # 'output' key should not be present.
    assert "output" not in dummy_response_ctx.extra

    # Verify that the extract method was called and append was not.
    workflow.window.core.agents.tools.extract_tool_outputs.assert_called_once_with(dummy_response_ctx)
    workflow.window.core.agents.tools.append_tool_outputs.assert_not_called()