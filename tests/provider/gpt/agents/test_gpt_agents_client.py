#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import os
import pytest
from unittest.mock import MagicMock

from pygpt_net.provider.api.openai.agents.client import (
    CustomModelProvider,
    get_custom_model_provider,
    get_client,
    set_openai_env,
    MODE_AGENT_OPENAI,
)

def test_custom_model_provider_get_model(monkeypatch):
    fake_client = object()
    call_args = []
    def fake_OpenAIChatCompletionsModel(model, openai_client):
        call_args.append((model, openai_client))
        return MagicMock()
    monkeypatch.setattr("pygpt_net.provider.api.openai.agents.client.OpenAIChatCompletionsModel", fake_OpenAIChatCompletionsModel)
    provider = CustomModelProvider(fake_client)
    result = provider.get_model("test-model")
    assert call_args == [("test-model", fake_client)]
    assert result

def test_custom_model_provider_init(monkeypatch):
    flag = {"called": False}
    def fake_set_tracing_disabled(val):
        flag["called"] = True
    monkeypatch.setattr("pygpt_net.provider.api.openai.agents.client.set_tracing_disabled", fake_set_tracing_disabled)
    fake_client = MagicMock()
    provider = CustomModelProvider(fake_client)
    assert provider.client is fake_client
    assert flag["called"]

def test_get_custom_model_provider(monkeypatch):
    fake_args = {"dummy": "value"}
    fake_client = MagicMock()
    window = MagicMock()
    window.core.models.prepare_client_args.return_value = fake_args
    def fake_AsyncOpenAI(**kwargs):
        assert kwargs == fake_args
        return fake_client
    monkeypatch.setattr("pygpt_net.provider.api.openai.agents.client.AsyncOpenAI", fake_AsyncOpenAI)
    provider = get_custom_model_provider(window, MagicMock())
    assert isinstance(provider, CustomModelProvider)
    assert provider.client is fake_client

def test_get_client(monkeypatch):
    fake_args = {"dummy": "value"}
    fake_client = MagicMock()
    window = MagicMock()
    window.core.models.prepare_client_args.return_value = fake_args
    def fake_AsyncOpenAI(**kwargs):
        assert kwargs == fake_args
        return fake_client
    monkeypatch.setattr("pygpt_net.provider.api.openai.agents.client.AsyncOpenAI", fake_AsyncOpenAI)
    flag = {"called": False}
    def fake_set_tracing_disabled(val):
        flag["called"] = True
    monkeypatch.setattr("pygpt_net.provider.api.openai.agents.client.set_tracing_disabled", fake_set_tracing_disabled)
    client = get_client(window, MagicMock())
    assert client is fake_client
    assert flag["called"]

def test_set_openai_env(monkeypatch):
    config_values = {
        "api_key": "key_value",
        "api_endpoint": "endpoint_value",
        "organization_key": "org_value"
    }
    fake_config = MagicMock()
    fake_config.get.side_effect = lambda key: config_values.get(key)
    window = MagicMock()
    window.core.config = fake_config
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_API_BASE", None)
    os.environ.pop("OPENAI_ORGANIZATION", None)
    set_openai_env(window)
    assert os.environ["OPENAI_API_KEY"] == "key_value"
    assert os.environ["OPENAI_API_BASE"] == "endpoint_value"
    assert os.environ["OPENAI_ORGANIZATION"] == "org_value"