"""Dispatch contracts for synchronous and asynchronous legacy agent engines."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pygpt_net.core.agents.execution import AgentExecution
from pygpt_net.core.types import (AGENT_MODE_ASSISTANT, AGENT_MODE_PLAN, AGENT_MODE_STEP,
                                 AGENT_MODE_WORKFLOW, AGENT_MODE_OPENAI)


def prepared(mode, schema=None):
    item = MagicMock()
    item.provider.get_mode.return_value = mode
    item.agent_kwargs = {'schema': schema, 'system_prompt': 'instructions'}
    item.execution_kwargs.side_effect = lambda: {'agent': item.agent, 'ctx': item.context.ctx, 'prompt': 'task'}
    item.prompt = 'task'
    item.agent.name = 'Worker'
    return item


@pytest.mark.parametrize('mode,engine', [(AGENT_MODE_PLAN, 'llama_plan'), (AGENT_MODE_STEP, 'llama_steps'),
                                       (AGENT_MODE_ASSISTANT, 'llama_assistant')])
def test_synchronous_dispatch_preserves_schema(mode, engine):
    runner = MagicMock()
    execution = AgentExecution(runner)
    request = prepared(mode, {'nodes': ['a']})
    assert execution.run(request) is getattr(runner, engine).run.return_value
    getattr(runner, engine).run.assert_called_once_with(**request.execution_kwargs(), schema={'nodes': ['a']})
    assert execution.workflow_bridge is None


@pytest.mark.parametrize('mode,engine,source', [(AGENT_MODE_WORKFLOW, 'llama_workflow', 'llama_index'),
                                              (AGENT_MODE_OPENAI, 'openai_workflow', 'openai_agents')])
def test_async_dispatch_starts_monitor_and_passes_engine_specific_context(mode, engine, source):
    runner = MagicMock()
    getattr(runner, engine).run = AsyncMock(return_value='done')
    execution, request = AgentExecution(runner), prepared(mode)
    with patch('pygpt_net.core.agents.execution.AgentWorkflowBridge') as bridge:
        assert execution.run(request) == 'done'
    assert bridge.call_args.kwargs['source'] == source
    assert bridge.call_args.kwargs['root_name'] == 'Worker'
    bridge.return_value.start.assert_called_once_with()
    kwargs = getattr(runner, engine).run.call_args.kwargs
    assert kwargs['workflow_bridge'] is bridge.return_value
    assert 'schema' not in kwargs
    if mode == AGENT_MODE_WORKFLOW:
        assert kwargs['session'] is request.session
        assert kwargs['history'] is request.history
        assert kwargs['llm'] is request.llm
    else:
        assert kwargs['run'] is request.provider.run
        assert kwargs['agent_kwargs'] is request.agent_kwargs
        assert kwargs['stream'] is request.stream
    error = RuntimeError('failed')
    execution.fail(error)
    bridge.return_value.fail.assert_called_once_with(error)


def test_quick_call_dispatch_and_unsupported_mode():
    runner = MagicMock()
    runner.llama_workflow.run_once = AsyncMock(return_value='answer')
    execution = AgentExecution(runner)
    request = prepared(AGENT_MODE_WORKFLOW)
    assert execution.run_once(request) == 'answer'
    kwargs = runner.llama_workflow.run_once.call_args.kwargs
    assert kwargs['is_expert_call'] is request.is_expert_call
    assert kwargs['session'] is request.session
    assert execution.workflow_bridge is None
    assert execution.run_once(prepared('unknown')) is None
    assert execution.run(prepared('unknown')) is None
    execution.fail(RuntimeError('no monitor yet'))
