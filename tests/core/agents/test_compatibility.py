"""Preset migration must preserve editable options without sharing mutable state."""
from types import SimpleNamespace

import pytest

from pygpt_net.core.agents.compatibility import OPENAI_TO_LLAMA, RETIRED_LLAMA_PROVIDERS, migrate_preset


def preset(**kwargs):
    return SimpleNamespace(**dict(dict(agent_openai=False, agent_llama=False, agent_provider='',
                                      agent_provider_openai='', name='Custom', extra={}), **kwargs))


@pytest.mark.parametrize('source,target', OPENAI_TO_LLAMA.items())
def test_migrate_openai_provider_and_copy_options(source, target):
    item = preset(agent_openai=True, agent_provider_openai=source, extra={source: {'options': ['a']}})
    migrate_preset(item)
    assert item.agent_provider == target
    assert item.agent_llama is True
    assert item.agent_openai is False
    if target.startswith('llama_agent_'):
        assert item.extra[target] == item.extra[source]
        item.extra[target]['options'].append('b')
        assert item.extra[source]['options'] == ['a']
    before = item.extra.copy()
    migrate_preset(item)
    assert item.extra == before


@pytest.mark.parametrize('provider', sorted(RETIRED_LLAMA_PROVIDERS))
@pytest.mark.parametrize('name,expected', [('OpenAI Agent', 'Simple agent'), ('ReAct Agent', 'Simple agent'), ('Mine', 'Mine')])
def test_retired_llama_provider_names(provider, name, expected):
    item = preset(agent_provider=provider, agent_llama=True, name=name)
    migrate_preset(item)
    assert item.agent_provider == 'llama_agent_base'
    assert item.name == expected


def test_existing_target_options_and_unknown_providers_are_untouched():
    source, target = 'openai_agent_base', 'llama_agent_base'
    item = preset(agent_openai=True, agent_provider_openai=source, extra={source: {'x': 1}, target: {'x': 2}})
    migrate_preset(item)
    assert item.extra[target] == {'x': 2}
    item = preset(agent_openai=True, agent_provider_openai='third-party', extra=None)
    migrate_preset(item)
    assert item.agent_openai is True
    assert item.agent_provider == ''
