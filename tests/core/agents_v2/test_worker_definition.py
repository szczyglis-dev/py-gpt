"""Specialist rebuilding preserves memory and installs Swarm message receivers."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents_v2.worker_definition import WorkerDefinition


def runtime(swarm=False):
    rt = MagicMock()
    rt.run_id = 'run'
    rt.is_swarm_mode = swarm
    rt.workers.next_id.return_value = 'w'
    rt.workers.created_count = 2
    rt.workers.number.return_value = 3
    rt.status.worker_name.side_effect = lambda name, number: f'Agent {number}: {name}'
    rt.window.core.context_manager.enabled.return_value = False
    rt.bridge_system_prompt = 'bridge'
    rt.runtime_system_context = 'environment'
    rt.strategy.worker_prompt = 'worker base'
    rt.strategy.worker_controller_tag = 'controller'
    rt.window.core.skills.prompt_catalog.return_value = ''
    rt.inputs.rag_prompt.return_value = 'RAG'
    return rt


@pytest.mark.parametrize('swarm', [False, True])
@pytest.mark.parametrize('managed', [False, True])
def test_create_builds_memory_tools_and_agent(swarm, managed):
    rt = runtime(swarm)
    rt.window.core.context_manager.enabled.return_value = managed
    communication = MagicMock()
    definition = WorkerDefinition(rt, communication)
    with patch('pygpt_net.core.agents_v2.worker_definition.Memory') as memory:
        state, number = definition.create('Writer', 'Write', 'x' * 100, 'system')
    assert state.id == 'w' and len(state.language) == 80
    assert number == (3 if swarm else 0)
    assert state.name == ('Agent 3: Writer' if swarm else 'Writer')
    assert state.agent is rt.inputs.agent.return_value
    assert state.tool_ctx is rt.artifacts.worker_context.return_value
    if managed:
        memory.from_defaults.assert_not_called()
        assert state.memory is rt.window.core.context_manager.build_agent_memory.return_value
    else:
        assert state.memory is memory.from_defaults.return_value
        assert memory.from_defaults.call_args.kwargs['session_id'] == 'agents_v2_run_w'
    if swarm:
        state.agent.set_message_receiver.call_args.args[0]()
        communication.receive.assert_called_once_with('w')
    else:
        state.agent.set_message_receiver.assert_not_called()


@pytest.mark.parametrize('swarm', [False, True])
def test_update_preserves_memory_and_normalizes_fields(swarm):
    rt = runtime(swarm)
    communication = MagicMock()
    definition = WorkerDefinition(rt, communication)
    state = SimpleNamespace(id='w', name='Old', instruction='old', language='pl', system_prompt='old', memory=object())
    original_memory = state.memory
    definition.update(state, ' New ', ' work ', ' en ', ' system ')
    assert state.name == ('Agent 3: New' if swarm else 'New')
    assert state.instruction == 'work' and state.language == 'en' and state.system_prompt == 'system'
    assert state.memory is original_memory
    definition.update(state, '', ' ', None, '')
    assert state.instruction == 'work' and state.language == 'en' and state.system_prompt == ''
    if swarm:
        state.agent.set_message_receiver.call_args.args[0]()
        communication.receive.assert_called_once_with('w')


def test_prompt_does_not_duplicate_bridge_context_and_survives_skills_failure():
    rt = runtime()
    rt.bridge_system_prompt = 'bridge includes environment'
    definition = WorkerDefinition(rt, MagicMock())
    prompt = definition._prompt('Writer', 'Write', 'pl', 'instruction')
    assert '<runtime_environment>' not in prompt
    assert '<controller>\ninstruction\n</controller>' in prompt
    assert '<worker_identity>\nname=Writer\nrole_instruction=Write' in prompt
    rt.window.core.skills.prompt_catalog.side_effect = RuntimeError('catalog failed')
    rt.bridge_system_prompt = ''
    prompt = definition._prompt('Writer', 'Write', 'pl', '')
    assert '<runtime_environment>\nenvironment' in prompt
    assert '<controller>' not in prompt
    rt.window.core.debug.log.assert_called_once()
