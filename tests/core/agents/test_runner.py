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

import asyncio
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from pygpt_net.core.agents.runner import Runner
from pygpt_net.core.types import (
    AGENT_MODE_ASSISTANT,
    AGENT_MODE_PLAN,
    AGENT_MODE_STEP,
    AGENT_MODE_WORKFLOW,
    AGENT_MODE_OPENAI,
)

# Fixture for a dummy window with necessary attributes
@pytest.fixture
def dummy_window():
    win = MagicMock()
    win.controller = MagicMock()
    win.controller.kernel = MagicMock()
    win.controller.kernel.stopped.return_value = False
    win.core = MagicMock()
    win.core.config = MagicMock()
    win.core.config.get.side_effect = lambda key, default=None: {
        "agent.llama.verbose": False,
        "agent.llama.steps": 10,
        "stream": False,
    }.get(key, default)
    win.core.config.get_workdir_prefix.return_value = "test_workdir"
    win.core.command = MagicMock()
    win.core.command.is_cmd.return_value = True
    win.core.agents = MagicMock()
    win.core.agents.memory = MagicMock()
    win.core.agents.memory.prepare.return_value = []
    win.core.idx = MagicMock()
    win.core.idx.llm = MagicMock()
    win.core.idx.llm.get.return_value = "dummy_llm"
    win.core.idx.is_valid.return_value = False
    win.core.command.get_functions.return_value = []
    win.core.agents.tools = MagicMock()
    win.core.agents.tools.prepare.return_value = ["tool1"]
    win.core.agents.tools.get_function_tools.return_value = ["ftool"]
    win.core.agents.tools.get_plugin_tools.return_value = ["ptool"]
    win.core.agents.tools.get_plugin_specs.return_value = ["pspec"]
    win.core.agents.tools.get_retriever_tool.return_value = "retriever"
    win.core.agents.provider = MagicMock()
    win.core.agents.custom = MagicMock()
    win.core.debug = MagicMock()
    win.core.debug.error = MagicMock()
    return win

# Fixture for a dummy context
@pytest.fixture
def dummy_context():
    return SimpleNamespace(
        ctx=SimpleNamespace(extra={}, hidden_input=""),
        prompt="dummy prompt",
        model=SimpleNamespace(id="dummy_model"),
        system_prompt="dummy system prompt",
        preset=MagicMock(),
        mode="agent_llama",
        is_expert_call=False,
    )

# Fixture for signals
@pytest.fixture
def dummy_signals():
    return MagicMock()

# Helper to create a dummy provider with a given mode
def dummy_provider(mode):
    prov = MagicMock()
    prov.get_mode.return_value = mode
    prov.get_agent.return_value = "dummy_agent"
    prov.run = MagicMock()
    return prov

# Returns True if kernel is stopped
def test_call_stopped(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = True
    runner = Runner(dummy_window)
    result = runner.call(dummy_context, extra={}, signals=dummy_signals)
    assert result is True

# Returns False and sets error if provider is not found
def test_agent_not_found(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = False
    dummy_window.core.agents.provider.has.return_value = False
    dummy_window.core.agents.provider.get.return_value = MagicMock()
    runner = Runner(dummy_window)
    result = runner.call(dummy_context, extra={"agent_provider": "non_existent"}, signals=dummy_signals)
    assert result is False
    assert runner.get_error() is not None
    dummy_window.core.debug.log.assert_called_once()

# Test runner using AGENT_MODE_PLAN
def test_agent_plan(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = False
    prov = dummy_provider(AGENT_MODE_PLAN)
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.agents.provider.get.return_value = prov
    runner = Runner(dummy_window)
    runner.llama_plan.run = lambda **kwargs: True
    result = runner.call(dummy_context, extra={"agent_provider": "plan_agent", "agent_idx": 1}, signals=dummy_signals)
    assert result is True

# Test runner using AGENT_MODE_STEP
def test_agent_step(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = False
    prov = dummy_provider(AGENT_MODE_STEP)
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.agents.provider.get.return_value = prov
    runner = Runner(dummy_window)
    runner.llama_steps.run = lambda **kwargs: True
    result = runner.call(dummy_context, extra={"agent_provider": "step_agent"}, signals=dummy_signals)
    assert result is True

# Test runner using AGENT_MODE_ASSISTANT
def test_agent_assistant(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = False
    prov = dummy_provider(AGENT_MODE_ASSISTANT)
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.agents.provider.get.return_value = prov
    runner = Runner(dummy_window)
    runner.llama_assistant.run = lambda **kwargs: True
    result = runner.call(dummy_context, extra={"agent_provider": "assistant_agent"}, signals=dummy_signals)
    assert result is True

# Test runner using AGENT_MODE_WORKFLOW with an async workflow run
def test_agent_workflow(dummy_window, dummy_context, dummy_signals, monkeypatch):
    dummy_window.controller.kernel.stopped.return_value = False
    prov = dummy_provider(AGENT_MODE_WORKFLOW)
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.agents.provider.get.return_value = prov

    session = MagicMock()
    monkeypatch.setattr("pygpt_net.core.agents.preparation.LlamaSession", MagicMock(return_value=session))
    agent_tools = MagicMock()
    monkeypatch.setattr("pygpt_net.core.agents.preparation.Tools", MagicMock(return_value=agent_tools))
    monkeypatch.setattr("pygpt_net.core.agents.preparation.ComputerRuntime", MagicMock(return_value=MagicMock()))
    bridge = MagicMock()
    monkeypatch.setattr("pygpt_net.core.agents.execution.AgentWorkflowBridge", MagicMock(return_value=bridge))

    runner = Runner(dummy_window)

    async def fake_workflow_run(**kwargs):
        assert kwargs["session"] is session
        return True

    runner.llama_workflow.run = fake_workflow_run
    result = runner.call(dummy_context, extra={"agent_provider": "workflow_agent"}, signals=dummy_signals)
    assert result is True
    session.bind_llm.assert_called_once()
    bridge.start.assert_called_once_with()

# Test runner using AGENT_MODE_OPENAI with an async openai run
def test_agent_openai(dummy_window, dummy_context, dummy_signals):
    dummy_window.controller.kernel.stopped.return_value = False
    prov = dummy_provider(AGENT_MODE_OPENAI)
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.agents.provider.get.return_value = prov
    runner = Runner(dummy_window)

    async def fake_openai_run(**kwargs):
        return True

    runner.openai_workflow.run = fake_openai_run
    result = runner.call(dummy_context, extra={"agent_provider": "openai"}, signals=dummy_signals)
    assert result is True

def test_quick_call_preserves_explicit_tools_history_and_index_when_commands_disabled(
        dummy_window, dummy_context, dummy_signals, monkeypatch):
    from pygpt_net.core.agents.preparation import AgentPreparation
    provider = dummy_provider(AGENT_MODE_WORKFLOW)
    dummy_window.core.agents.provider.get.return_value = provider
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.command.is_cmd.return_value = False
    dummy_context.preset.idx = "preset-index"
    session = MagicMock()
    tools = MagicMock()
    monkeypatch.setattr("pygpt_net.core.agents.preparation.LlamaSession", lambda *args, **kwargs: session)
    monkeypatch.setattr("pygpt_net.core.agents.preparation.Tools", lambda *args, **kwargs: tools)
    monkeypatch.setattr("pygpt_net.core.agents.preparation.ComputerRuntime", lambda *args, **kwargs: object())
    history = []
    explicit_tools = [object()]
    prepared = AgentPreparation(dummy_window, ["react"], "ADDITIONAL CONTEXT:").prepare(
        dummy_context, {"agent_idx": "explicit-index", "agent_tools": explicit_tools,
                        "agent_history": history}, dummy_signals, "workflow", False, once=True)
    assert prepared.agent_kwargs["tools"] is explicit_tools
    assert prepared.history is history
    assert prepared.agent_kwargs["plugin_tools"] == {}
    assert dummy_context.ctx.extra["agent_output"] is True
    tools.set_idx.assert_called_once_with("explicit-index")
    tools.prepare.assert_not_called()
    dummy_window.core.agents.memory.prepare.assert_not_called()
    dummy_window.core.idx.chat.query_retrieval.assert_not_called()
    assert not hasattr(dummy_context.ctx, "agents_v2_system_prompt")


def test_regular_call_uses_preset_index_and_persists_composed_prompt(
        dummy_window, dummy_context, dummy_signals, monkeypatch):
    from pygpt_net.core.agents.preparation import AgentPreparation
    provider = dummy_provider(AGENT_MODE_WORKFLOW)
    dummy_window.core.agents.provider.get.return_value = provider
    dummy_window.core.agents.provider.has.return_value = True
    dummy_window.core.command.is_cmd.return_value = False
    dummy_context.preset.idx = "preset-index"
    dummy_window.core.idx.chat.query_retrieval.return_value = "retrieved context"
    tools = MagicMock()
    monkeypatch.setattr("pygpt_net.core.agents.preparation.LlamaSession", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr("pygpt_net.core.agents.preparation.Tools", lambda *args, **kwargs: tools)
    monkeypatch.setattr("pygpt_net.core.agents.preparation.ComputerRuntime", lambda *args, **kwargs: object())
    extra = {"agent_idx": "explicit-index"}
    prepared = AgentPreparation(dummy_window, ["react"], "ADDITIONAL CONTEXT:").prepare(
        dummy_context, extra, dummy_signals, "workflow", False)
    assert extra["agent_idx"] == "preset-index"
    tools.set_idx.assert_called_once_with("preset-index")
    assert "retrieved context" in prepared.prompt
    assert "retrieved context" in dummy_context.ctx.hidden_input
    assert dummy_context.ctx.agents_v2_system_prompt.startswith("dummy system prompt")
    assert prepared.agent_kwargs["system_prompt_extra"] == prepared.agent_kwargs["system_prompt"]
    for name in ("tools", "function_tools", "plugin_tools", "plugin_specs"):
        assert prepared.agent_kwargs[name] == []
    assert prepared.agent_kwargs["retriever_tool"] is tools.get_retriever_tool.return_value


def test_quick_call_passes_once_policy_and_records_failure():
    from unittest.mock import patch
    from types import SimpleNamespace
    from pygpt_net.core.agents.runner import Runner
    window = MagicMock()
    window.controller.kernel.stopped.return_value = False
    runner = Runner(window)
    runner.preparation = MagicMock()
    ctx = SimpleNamespace(mode='agent_llama')
    signals = MagicMock()
    with patch('pygpt_net.core.agents.runner.AgentExecution') as execution:
        execution.return_value.run_once.return_value = 'answer'
        assert runner.call_once(ctx, {}, signals) == 'answer'
    assert runner.preparation.prepare.call_args.kwargs['once'] is True
    runner.preparation.prepare.side_effect = RuntimeError('bad')
    runner._record_error = MagicMock()
    assert runner.call_once(ctx, {}, signals) is None
    runner._record_error.assert_called_once()
    window.controller.kernel.stopped.return_value = True
    assert runner.call_once(ctx, {}, signals) is True
