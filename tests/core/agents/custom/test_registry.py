"""Custom agent CRUD, lazy loading, and generated editor options."""
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.agents.custom import Custom
from pygpt_net.item.agent import AgentItem


@pytest.fixture
def registry():
    core = Custom(MagicMock())
    core.provider = MagicMock()
    item = AgentItem()
    item.id, item.name = 'existing', 'Writer'
    core.provider.load.return_value = {'layout': 'layout', 'agents': {item.id: item}}
    return core


@pytest.mark.parametrize('method,args,expected', [
    ('get_layout', (), 'layout'), ('get_ids', (), ['existing']),
    ('get_choices', (), [{'existing': 'Writer *'}]),
    ('is_custom', ('existing',), True), ('is_custom', ('missing',), False),
    ('get_agent', ('missing',), None), ('get_schema', ('missing',), []),
    ('build_options', ('missing',), {}),
])
def test_read_methods_load_once(registry, method, args, expected):
    assert getattr(registry, method)(*args) == expected
    assert getattr(registry, method)(*args) == expected
    registry.provider.load.assert_called_once_with()


def test_reload_save_layout_and_reset(registry):
    registry.load()
    assert registry.get_agents()['existing'] is registry.get_agent('existing')
    registry.layout = None
    registry.update_layout({'x': 1})  # use a real layout instead of the provider placeholder
    assert registry.layout.data == {'x': 1}
    registry.save()
    registry.provider.save.assert_called_once_with(registry.layout, registry.agents)
    registry.reload()
    assert registry.loaded is True
    assert registry.provider.load.call_count == 2
    registry.reset()
    assert registry.agents == {} and registry.layout is None and not registry.loaded
    registry.provider.truncate.assert_called_once_with()


def test_crud_preserves_original_when_duplicating(registry):
    new_id = registry.new_agent('New')
    assert registry.get_agent(new_id).name == 'New'
    registry.update_agent(new_id, {'position': 1}, [{'id': 'agent1'}])
    assert registry.get_agent(new_id).schema == [{'id': 'agent1'}]
    registry.duplicate_agent(new_id, 'Copy')
    copied = next(item for item in registry.agents.values() if item.name == 'Copy')
    assert copied.id != new_id
    copied.schema.append({'id': 'agent2'})
    assert registry.get_agent(new_id).schema == [{'id': 'agent1'}]
    registry.update_agent(new_id, None, None)
    assert registry.get_agent(new_id).layout == {} and registry.get_schema(new_id) == []
    registry.delete_agent(new_id)
    assert not registry.is_custom(new_id)
    registry.provider.save.reset_mock()
    registry.delete_agent('missing')
    registry.duplicate_agent('missing', 'Copy')
    registry.update_agent('missing', {}, [])
    registry.provider.save.assert_not_called()


def test_editor_options_skip_non_agents_and_log_invalid_schema_nodes(registry, monkeypatch):
    monkeypatch.setattr('pygpt_net.core.agents.custom.trans', lambda key: key)
    registry.load()
    registry.agents['existing'].schema = [None, {'type': 'start'}, {'type': 'agent'},
        {'type': 'agent', 'id': 'a', 'slots': dict(name='Writer', role='writing', instruction='Write',
                                                remote_tools=False, local_tools=True)}]
    options = registry.build_options('existing')
    assert set(options) == {'a'}
    assert options['a']['label'] == 'Writer'
    opts = options['a']['options']
    assert opts['role']['default'] == 'writing'
    assert opts['prompt']['default'] == 'Write'
    assert opts['allow_remote_tools']['default'] is False
    assert opts['allow_local_tools']['default'] is True
    assert opts['model_overwrite']['default'] is False
    registry.window.core.debug.log.assert_called_once()
