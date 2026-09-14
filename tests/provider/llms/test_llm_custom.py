#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 12:30:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.types import MODE_CHAT, MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.custom import CustomLLM


def _window():
    return SimpleNamespace(
        core=SimpleNamespace(
            config=MagicMock(),
            models=MagicMock(),
            api=SimpleNamespace(openai=MagicMock(), logger=MagicMock()),
        )
    )


def test_init_and_api_key_placeholder():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://api.example/v1",
        api_key="",
    )

    assert provider.id == "custom_test_12345678"
    assert provider.name == "Test API"
    assert provider.api_base == "https://api.example/v1"
    assert provider.type == [MODE_LLAMA_INDEX, "embeddings"]
    assert provider.is_runtime_custom is True
    assert provider.get_api_key() == "custom"


def test_get_api_key_returns_configured_key():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://api.example/v1",
        api_key="SECRET",
    )

    assert provider.get_api_key() == "SECRET"


def test_llama_uses_openai_like_with_provider_defaults():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://api.example/v1",
        api_key="SECRET",
    )
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, cfg: args)

    model = ModelItem("model-a")
    model.ctx = 32000
    model.tool_calls = True
    model.llama_index = {
        "args": [
            {"name": "temperature", "type": "float", "value": 0.3},
        ]
    }
    window = _window()
    window.core.models.prepare_client_args.return_value = {
        "api_key": "SECRET",
        "base_url": "https://api.example/v1",
    }
    llm_instance = object()

    with patch("llama_index.llms.openai_like.OpenAILike", return_value=llm_instance) as openai_like:
        result = provider.llama(window=window, model=model, stream=True)

    assert result is llm_instance
    kwargs = openai_like.call_args.kwargs
    assert kwargs["model"] == "model-a"
    assert kwargs["api_key"] == "SECRET"
    assert kwargs["api_base"] == "https://api.example/v1"
    assert kwargs["temperature"] == 0.3
    assert kwargs["is_chat_model"] is True
    assert kwargs["is_function_calling_model"] is True
    assert kwargs["context_window"] == 32000
    provider.inject_llamaindex_http_clients.assert_called_once_with(kwargs, window.core.config)


def test_llama_per_model_api_configuration_has_priority():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://provider.example/v1",
        api_key="PROVIDER-KEY",
    )
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, cfg: args)

    model = ModelItem("model-a")
    model.custom_api_endpoint = "https://model.example/v1"
    model.custom_api_key = "MODEL-KEY"
    window = _window()
    window.core.models.prepare_client_args.return_value = {
        "api_key": "MODEL-KEY",
        "base_url": "https://model.example/v1",
    }

    with patch("llama_index.llms.openai_like.OpenAILike", return_value="LLM") as openai_like:
        result = provider.llama(window=window, model=model)

    assert result == "LLM"
    kwargs = openai_like.call_args.kwargs
    assert kwargs["api_key"] == "MODEL-KEY"
    assert kwargs["api_base"] == "https://model.example/v1"


def test_get_client_routes_through_openai_api_using_runtime_provider_id():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://api.example/v1",
        api_key="KEY",
    )
    window = _window()
    client = object()
    window.core.api.openai.get_client.return_value = client

    result = provider.get_client(window)

    assert result is client
    kwargs = window.core.api.openai.get_client.call_args.kwargs
    assert kwargs["mode"] == MODE_CHAT
    assert kwargs["model"].provider == provider.id


def test_get_models_returns_openai_compatible_model_list():
    provider = CustomLLM(
        provider_id="custom_test_12345678",
        name="Test API",
        api_base="https://api.example/v1",
        api_key="KEY",
    )
    client = MagicMock()
    client.models.list.return_value = SimpleNamespace(
        data=[SimpleNamespace(id="model-a"), SimpleNamespace(id="model-b")]
    )
    provider.get_client = MagicMock(return_value=client)

    result = provider.get_models(_window())

    assert result == [
        {"id": "model-a", "name": "model-a"},
        {"id": "model-b", "name": "model-b"},
    ]
    client.models.list.assert_called_once_with()
