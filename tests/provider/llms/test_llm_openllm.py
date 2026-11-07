#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.types.reasoning import PROVIDER_REASONING_EFFORTS
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.openllm.provider import OpenLLMLLM

BASE_URL = "http://127.0.0.1:8787/v1"


def _window(api_key="placeholder", base_url=BASE_URL):
    config = MagicMock()
    config.get.return_value = None
    return SimpleNamespace(
        core=SimpleNamespace(
            config=config,
            api=SimpleNamespace(logger=MagicMock()),
            debug=MagicMock(),
            models=SimpleNamespace(
                prepare_client_args=MagicMock(
                    return_value={"api_key": api_key, "base_url": base_url}
                )
            ),
        )
    )


def _card(model_id, **extra):
    return SimpleNamespace(id=model_id, model_extra=extra)


def test_setup_defaults_to_local_daemon_with_optional_key():
    setup = OpenLLMLLM().setup()

    assert setup["openai_compatible"] is True
    assert setup["require_api_key"] is False
    assert setup["settings"]["api_base"]["default"] == BASE_URL
    assert setup["settings"]["api_key"]["secret"] is True
    assert setup["settings"]["api_key"]["default"] == ""
    assert setup["settings"]["api_key"]["env"] == ["OPENLLM_API_KEY"]


def test_chat_only_provider():
    provider = OpenLLMLLM()

    assert provider.id == "openllm"
    assert provider.type == ["llama_index"]
    assert "openllm" in PROVIDER_REASONING_EFFORTS


def test_llama_uses_provider_settings():
    provider = OpenLLMLLM()
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, cfg: args)
    model = ModelItem("lite")
    model.provider = "openllm"
    model.tool_calls = True
    model.llama_index = {"args": []}

    with patch("llama_index.llms.openai_like.OpenAILike", return_value="LLM") as openai_like:
        result = provider.llama(_window(), model)

    assert result == "LLM"
    kwargs = openai_like.call_args.kwargs
    assert kwargs["model"] == "lite"
    assert kwargs["api_base"] == BASE_URL
    assert kwargs["api_key"] == "placeholder"
    assert kwargs["is_chat_model"] is True
    assert kwargs["is_function_calling_model"] is True


def test_llama_passes_configured_key():
    provider = OpenLLMLLM()
    provider.inject_llamaindex_http_clients = MagicMock(side_effect=lambda args, cfg: args)
    model = ModelItem("plus")
    model.provider = "openllm"
    model.llama_index = {"args": []}

    with patch("llama_index.llms.openai_like.OpenAILike", return_value="LLM") as openai_like:
        provider.llama(_window(api_key="CONFIG-KEY", base_url="https://www.openllm.sh/v1"), model)

    kwargs = openai_like.call_args.kwargs
    assert kwargs["api_key"] == "CONFIG-KEY"
    assert kwargs["api_base"] == "https://www.openllm.sh/v1"


def test_environment_names():
    keys, bases = OpenLLMLLM().get_openai_compatible_env_names()

    assert keys[0] == "OPENLLM_API_KEY"
    assert not any("OPENLLM" in name for name in bases)


def test_get_models_keeps_chat_models_and_reads_card_metadata():
    provider = OpenLLMLLM()
    cards = [
        _card(
            "claude_code/claude-opus-4-8",
            capabilities=["chat", "vision", "tools", "streaming"],
            context_window=200000,
            max_output_tokens=32000,
        ),
        _card("lite", capabilities=["chat", "streaming"]),
        _card("openai/text-embedding-3-small", capabilities=["embedding"]),
        _card("openai/gpt-image-2", capabilities=["image_generation"]),
        _card("legacy-card"),
    ]
    client = SimpleNamespace(models=SimpleNamespace(list=lambda: SimpleNamespace(data=cards)))
    provider.get_client = MagicMock(return_value=client)

    items = provider.get_models(_window())
    by_id = {item["id"]: item for item in items}

    assert list(by_id) == ["claude_code/claude-opus-4-8", "lite", "legacy-card"]
    opus = by_id["claude_code/claude-opus-4-8"]
    assert opus["input"] == ["text", "image"]
    assert opus["tool_calls"] is True
    assert opus["ctx"] == 200000
    assert opus["tokens"] == 32000
    assert by_id["lite"]["input"] == ["text"]
    assert by_id["lite"]["tool_calls"] is False
    assert "ctx" not in by_id["lite"]
    assert "tool_calls" not in by_id["legacy-card"]


def test_get_models_returns_empty_list_when_unreachable():
    provider = OpenLLMLLM()
    provider.get_client = MagicMock(side_effect=RuntimeError("connection refused"))
    window = _window()

    assert provider.get_models(window) == []
    window.core.debug.log.assert_called_once()


def test_blank_api_key_falls_back_to_placeholder_but_is_not_stored():
    provider = OpenLLMLLM()
    provider.window = SimpleNamespace(
        core=SimpleNamespace(
            config=SimpleNamespace(get_provider=lambda cid, key, default=None: default),
        )
    )

    assert provider.get_config("api_key", "") == "openllm"
    assert provider.get_config("api_base") == BASE_URL


def test_configured_api_key_is_used_as_is():
    provider = OpenLLMLLM()
    provider.window = SimpleNamespace(
        core=SimpleNamespace(
            config=SimpleNamespace(get_provider=lambda cid, key, default=None: "sk-llm-test.secret"),
        )
    )

    assert provider.get_config("api_key", "") == "sk-llm-test.secret"
