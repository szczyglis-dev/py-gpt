"""OpenAI custom-node construction keeps route policy, tools, and handoffs separate."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.agents.custom.factory import AgentFactory
from pygpt_net.core.agents.custom.utils import NodeRuntime


@pytest.mark.parametrize('routes,force', [(['a'], False), (['a', 'b'], False), (['a'], True)])
@pytest.mark.parametrize('handoffs', [False, True])
def test_factory_builds_runtime_and_injects_router_only_when_needed(routes, force, handoffs):
    window, logger = MagicMock(), MagicMock()
    factory = AgentFactory(window, logger)
    node = SimpleNamespace(id='writer', name=' Writer ', outputs=routes)
    runtime = NodeRuntime(SimpleNamespace(name='model'), 'instruction', None, True, False)
    with patch('pygpt_net.core.agents.custom.factory.OpenAIAgent') as agent, \
         patch('pygpt_net.core.agents.custom.factory.append_tools', return_value={'tools': ['tool']}) as tools, \
         patch('pygpt_net.core.agents.custom.factory.get_experts', return_value=['expert']) as experts, \
         patch('pygpt_net.core.agents.custom.factory.build_router_instruction', return_value='route instruction'):
        built = factory.build(node, runtime, None, ['function'], force, {'a': 'A'}, handoffs_enabled=handoffs)
    assert built.instance is agent.return_value and built.name == 'Writer'
    assert built.multi_output is (force or len(routes) > 1)
    assert built.allowed_routes == routes and built.allowed_routes is not routes
    assert built.instructions == ('route instruction\n\ninstruction' if built.multi_output else 'instruction')
    assert agent.call_args.kwargs['tools'] == ['tool']
    assert agent.call_args.kwargs.get('handoffs', []) == (['expert'] if handoffs else [])
    assert tools.call_args.kwargs['allow_remote_tools'] is False
    if not handoffs:
        experts.assert_not_called()
