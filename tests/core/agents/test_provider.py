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
from pygpt_net.core.agents.provider import Provider

# Dummy agent for testing, having minimal attributes required: name and type.
class DummyAgent:
    def __init__(self, name, agent_type):
        self.name = name
        self.type = agent_type

@pytest.fixture
def provider():
    return Provider()

def test_get_ids_empty(provider):
    # No agents registered so list should be empty
    assert provider.get_ids() == []

def test_register_and_get(provider):
    dummy = DummyAgent(name="Agent1", agent_type="A")
    provider.register("agent1", dummy)
    # Check registration, existence, and retrieval
    assert provider.has("agent1")
    assert provider.get("agent1") == dummy
    assert provider.get_ids() == ["agent1"]

def test_all_agents(provider):
    agent1 = DummyAgent(name="Agent1", agent_type="A")
    agent2 = DummyAgent(name="Agent2", agent_type="B")
    provider.register("agent1", agent1)
    provider.register("agent2", agent2)
    all_agents = provider.all()
    assert isinstance(all_agents, dict)
    assert all_agents == {"agent1": agent1, "agent2": agent2}

def test_get_providers(provider):
    agent1 = DummyAgent(name="Agent1", agent_type="A")
    provider.register("agent1", agent1)
    # Both methods return the same list
    assert provider.get_providers() == provider.get_ids()

def test_get_choices_no_filter(provider):
    # Register agents in unsorted order to test sorting by agent name
    agent_a = DummyAgent(name="Charlie", agent_type="A")
    agent_b = DummyAgent(name="Alpha", agent_type="A")
    agent_c = DummyAgent(name="Bravo", agent_type="A")
    provider.register("a", agent_a)
    provider.register("b", agent_b)
    provider.register("c", agent_c)
    choices = provider.get_choices()
    # Sorted alphabetically by agent name (case-insensitive)
    expected = [{"b": "Alpha"}, {"c": "Bravo"}, {"a": "Charlie"}]
    assert choices == expected

def test_get_choices_with_filter(provider):
    agent_a = DummyAgent(name="Alpha", agent_type="A")
    agent_b = DummyAgent(name="Beta", agent_type="B")
    agent_c = DummyAgent(name="Gamma", agent_type="A")
    provider.register("a", agent_a)
    provider.register("b", agent_b)
    provider.register("c", agent_c)
    # Filter on type "A"
    choices = provider.get_choices(type="A")
    expected = [{"a": "Alpha"}, {"c": "Gamma"}]
    assert choices == expected

@pytest.mark.parametrize('provider_name,sdk_class', [('openai', 'OpenAIResponsesModel'), ('azure_openai', 'OpenAIResponsesModel'), ('other', 'OpenAIChatCompletionsModel')])
def test_legacy_sdk_model_uses_configured_client(provider_name, sdk_class):
    from types import SimpleNamespace
    from unittest.mock import patch
    window = MagicMock()
    core = Provider(window)
    model = SimpleNamespace(id='model', provider=provider_name)
    window.core.models.prepare_client_args.return_value = {'api_key': 'test'}
    with patch('openai.AsyncOpenAI') as client, patch('agents.OpenAIResponsesModel') as responses, \
         patch('agents.OpenAIChatCompletionsModel') as chat, patch('agents.set_tracing_disabled') as tracing:
        result = core.get_openai_model(model)
    selected = responses if sdk_class == 'OpenAIResponsesModel' else chat
    assert result is selected.return_value
    selected.assert_called_once_with(model='model', openai_client=client.return_value)
    client.assert_called_once_with(api_key='test')
    tracing.assert_called_once_with(True)


def test_missing_legacy_sdk_model_raises_instead_of_using_global_credentials():
    core = Provider(MagicMock())
    core.window.core.models.get.return_value = None
    with pytest.raises(ValueError, match='Unable to resolve a model'):
        core.get_openai_model('missing')
