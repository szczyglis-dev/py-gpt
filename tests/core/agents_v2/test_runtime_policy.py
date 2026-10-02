"""Validated iteration limits and execution-mode facades."""
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.agents_v2.runtime import AgentsV2Runtime
from pygpt_net.core.agents_v2.mode import AgentMode
from pygpt_net.core.agents_v2.strategy import get_agent_strategy


@pytest.mark.parametrize('mode', list(AgentMode))
@pytest.mark.parametrize('value', [0, -1, 5, 'invalid', None])
def test_runtime_limits_and_identity(mode, value):
    runtime = object.__new__(AgentsV2Runtime)
    runtime.window = MagicMock()
    runtime.window.core.config.get.side_effect = lambda key, default=None: value
    runtime.agent_mode = mode
    runtime.strategy = get_agent_strategy(mode)
    runtime.agent_definition = None
    assert runtime.is_primary_agent_mode is (mode == AgentMode.PRIMARY_AGENT)
    assert runtime.is_swarm_mode is (mode == AgentMode.SWARM)
    assert runtime.is_orchestrator_mode is (mode == AgentMode.ORCHESTRATOR)
    assert runtime.uses_workflow_finish is runtime.strategy.uses_workflow_finish
    assert runtime.main_max_iterations > 0 and runtime.worker_max_iterations > 0
    expected = max(0, int(value)) if value not in (None, 'invalid') else runtime.MAX_WORKERS_DEFAULT
    assert runtime.max_workers_configured == expected
    assert runtime.main_agent_name == runtime.strategy.main_name
    assert runtime.main_event(' Done ') == runtime.strategy.event_prefix+' Done'
    runtime.agent_definition = {'name': 'Custom'}
    assert runtime.main_agent_name == 'Custom'
    assert runtime.main_agent_description == 'Custom Agents workflow'
