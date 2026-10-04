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
    # Tool outputs are now copied by add_ctx(with_tool_outputs=True).
    dummy_response_ctx = DummyCtx()
    add_ctx = MagicMock(return_value=dummy_response_ctx)
    monkeypatch.setattr(workflow, "add_ctx", add_ctx)

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

    add_ctx.assert_called_once_with(dummy_ctx, with_tool_outputs=True)


def test_make_response_without_tool_outputs(monkeypatch, workflow):
    # Tool outputs are now copied by add_ctx(with_tool_outputs=True).
    dummy_response_ctx = DummyCtx()
    add_ctx = MagicMock(return_value=dummy_response_ctx)
    monkeypatch.setattr(workflow, "add_ctx", add_ctx)

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

    add_ctx.assert_called_once_with(dummy_ctx, with_tool_outputs=True)


def test_legacy_openai_run_callbacks_keep_loader_until_real_prose_and_finalize():
    import asyncio
    from types import SimpleNamespace
    from pygpt_net.item.ctx import CtxItem
    window = MagicMock()
    workflow = OpenAIWorkflow(window)
    workflow.is_stopped = MagicMock(return_value=False)
    for name in ('set_busy', 'set_idle', 'send_stream', 'end_stream', 'next_stream', 'send_response', 'set_error'):
        setattr(workflow, name, MagicMock())
    ctx, next_ctx = CtxItem(), CtxItem()
    ctx.set_agent_name('Writer')
    workflow.add_next_ctx = MagicMock(return_value=next_ctx)
    workflow.make_response = MagicMock(return_value=ctx)
    window.core.agents.memory.prepare_openai.return_value = ([], 'previous')
    window.core.api.openai.vision.build_agent_input.return_value = [{'role': 'user', 'content': 'task'}]
    signals, monitor = MagicMock(), MagicMock()
    async def run(**kwargs):
        assert kwargs['previous_response_id'] == 'previous'
        assert kwargs['use_partial_ctx'] is True
        assert kwargs['schema'] == ['schema']
        bridge = kwargs['bridge']
        ctx.stream = ''
        bridge.on_step(ctx)
        workflow.send_stream.assert_not_called()
        ctx.stream = 'prose'
        bridge.on_step(ctx)
        workflow.send_stream.assert_called_once_with(ctx, signals, True)
        bridge.on_next(ctx)
        result = bridge.on_next_ctx(ctx, input='next', output='answer', response_id='r')
        assert result is next_ctx and next_ctx.partial is True
        bridge.on_next_ctx(ctx, input='done', output='done', response_id='r', finish=True)
        assert ctx.extra['agent_finish_evaluate'] is True
        bridge.on_error(RuntimeError('test'))
        bridge.on_stop(ctx)
        return ctx, 'final', 'response'
    context = SimpleNamespace(attachments=[])
    assert asyncio.run(workflow.run(MagicMock(), {'context': context, 'llm': 'unused'}, run,
                                    ctx, 'task', signals, schema=['schema'], workflow_bridge=monitor)) is True
    monitor.finish.assert_called_once_with('final')
    monitor.stop.assert_called_once()
    monitor.fail.assert_called_once()
    workflow.make_response.assert_called_once_with(ctx, 'task', 'final', 'response')
