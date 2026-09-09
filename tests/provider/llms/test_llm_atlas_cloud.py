#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.atlas_cloud import (
    ATLAS_CLOUD_DEFAULT_BASE_URL,
    AtlasCloudLLM,
)


def _window():
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "api_key_atlas_cloud": "CONFIG-KEY",
        "api_endpoint_atlas_cloud": ATLAS_CLOUD_DEFAULT_BASE_URL,
    }.get(key, default)
    return SimpleNamespace(
        core=SimpleNamespace(
            config=config,
            api=SimpleNamespace(openai=MagicMock()),
        )
    )


def test_llama_uses_atlas_cloud_defaults():
    provider = AtlasCloudLLM()
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, cfg: args)
    model = ModelItem("openai/gpt-4.1-mini")
    model.tool_calls = True
    model.llama_index = {"args": []}

    with patch("llama_index.llms.openai_like.OpenAILike", return_value="LLM") as openai_like:
        result = provider.llama(_window(), model)

    assert result == "LLM"
    assert openai_like.call_args.kwargs["model"] == "openai/gpt-4.1-mini"
    assert openai_like.call_args.kwargs["api_key"] == "CONFIG-KEY"
    assert openai_like.call_args.kwargs["api_base"] == ATLAS_CLOUD_DEFAULT_BASE_URL
    assert openai_like.call_args.kwargs["is_chat_model"] is True
    assert openai_like.call_args.kwargs["is_function_calling_model"] is True


def test_environment_overrides_empty_config(monkeypatch):
    window = _window()
    window.core.config.get.side_effect = lambda key, default=None: ""
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "ENV-KEY")
    monkeypatch.setenv("ATLASCLOUD_API_BASE", "https://atlas.example/v1")

    args = AtlasCloudLLM()._apply_auth({}, window)

    assert args == {
        "api_key": "ENV-KEY",
        "api_base": "https://atlas.example/v1",
    }


def test_get_models_uses_openai_compatible_endpoint():
    provider = AtlasCloudLLM()
    client = MagicMock()
    client.models.list.return_value = SimpleNamespace(
        data=[SimpleNamespace(id="openai/gpt-4.1-mini")]
    )
    provider.get_client = MagicMock(return_value=client)

    assert provider.get_models(_window()) == [
        {"id": "openai/gpt-4.1-mini", "name": "openai/gpt-4.1-mini"}
    ]
    client.models.list.assert_called_once_with()
