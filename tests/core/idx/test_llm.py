#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import os
import pytest
from unittest.mock import MagicMock
from tests.mocks import mock_window

from pygpt_net.item.model import ModelItem
from pygpt_net.core.idx.llm import Llm
from pygpt_net.core.types import MODE_LLAMA_INDEX, MODE_CHAT


@pytest.fixture
def patch_openai(monkeypatch):
    instances = []

    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            instances.append(self)

    monkeypatch.setattr("pygpt_net.core.idx.llm.OpenAI", DummyOpenAI)
    return DummyOpenAI, instances


def test_init_sets_all_envs(mock_window):
    mock_window.core.config.set("api_key", "KEY")
    mock_window.core.config.set("api_endpoint", "https://api.example.com")
    mock_window.core.config.set("organization_key", "ORG")
    llm = Llm(mock_window)

    llm.init()

    assert os.environ["OPENAI_API_KEY"] == "KEY"
    assert os.environ["OPENAI_API_BASE"] == "https://api.example.com"
    assert os.environ["OPENAI_ORGANIZATION"] == "ORG"


def test_get_calls_init_and_llama_with_stream_and_sets_initialized(mock_window):
    model = ModelItem()
    model.provider = "openai"
    provider = MagicMock()
    provider.init = MagicMock()
    provider.llama = MagicMock(return_value="LLM_INSTANCE")
    provider.llama_multimodal = MagicMock(return_value=None)
    mock_window.core.llm.llms = {"openai": provider}

    llm = Llm(mock_window)
    assert llm.initialized is False

    result = llm.get(model=model, stream=True)

    assert result == "LLM_INSTANCE"
    provider.init.assert_called_once()
    kwargs = provider.init.call_args.kwargs
    assert kwargs["window"] is mock_window
    assert kwargs["model"] is model
    assert kwargs["mode"] == MODE_LLAMA_INDEX
    assert kwargs["sub_mode"] == ""

    provider.llama.assert_called_once()
    llama_kwargs = provider.llama.call_args.kwargs
    assert llama_kwargs["window"] is mock_window
    assert llama_kwargs["model"] is model
    assert llama_kwargs["stream"] is True

    assert llm.initialized is True



def test_get_returns_default_openai_when_model_none_and_sets_env(mock_window, patch_openai):
    DummyOpenAI, instances = patch_openai
    mock_window.core.config.set("api_key", "KEYX")
    mock_window.core.config.set("api_endpoint", "https://api.test")
    mock_window.core.config.set("organization_key", "ORGX")

    llm = Llm(mock_window)
    result = llm.get(model=None)

    assert isinstance(result, DummyOpenAI)
    assert len(instances) == 1
    inst = instances[0]
    assert inst.kwargs["temperature"] == 0.0
    assert inst.kwargs["model"] == llm.default_model

    assert os.environ["OPENAI_API_KEY"] == "KEYX"
    assert os.environ["OPENAI_API_BASE"] == "https://api.test"
    assert os.environ["OPENAI_ORGANIZATION"] == "ORGX"


def test_get_returns_default_openai_when_provider_missing(mock_window, patch_openai):
    DummyOpenAI, instances = patch_openai
    model = ModelItem()
    model.provider = "not-registered"

    mock_window.core.llm.llms = {}

    llm = Llm(mock_window)
    result = llm.get(model=model)

    assert isinstance(result, DummyOpenAI)
    assert len(instances) == 1


def test_get_embeddings_provider_uses_config_and_logs_model_name(mock_window):
    mock_window.core.idx.log = MagicMock()
    provider_name = "provEmb"
    env_cfg = [{"name": "ENV_A", "value": "X"}]
    args_cfg = [{"name": "model_name", "value": "EMB-1"}]

    mock_window.core.config.set("llama.idx.embeddings.provider", provider_name)
    mock_window.core.config.set("llama.idx.embeddings.env", env_cfg)
    mock_window.core.config.set("llama.idx.embeddings.args", args_cfg)

    emb_provider = MagicMock()
    emb_provider.init_embeddings = MagicMock()
    emb_provider.get_embeddings_model = MagicMock(return_value="EMB_MODEL")
    mock_window.core.llm.llms = {provider_name: emb_provider}

    llm = Llm(mock_window)
    result = llm.get_embeddings_provider()

    assert result == "EMB_MODEL"
    emb_provider.init_embeddings.assert_called_once()
    assert emb_provider.init_embeddings.call_args.kwargs["window"] is mock_window
    assert emb_provider.init_embeddings.call_args.kwargs["env"] == env_cfg

    emb_provider.get_embeddings_model.assert_called_once()
    assert emb_provider.get_embeddings_model.call_args.kwargs["window"] is mock_window
    assert emb_provider.get_embeddings_model.call_args.kwargs["config"] == args_cfg

    mock_window.core.idx.log.assert_called_with(
        f"Embeddings: using global provider: {provider_name}, model_name: EMB-1"
    )


def test_get_embeddings_provider_falls_back_to_default_provider_when_missing(mock_window):
    mock_window.core.idx.log = MagicMock()
    mock_window.core.config.set("llama.idx.embeddings.provider", "missing-provider")
    mock_window.core.config.set("llama.idx.embeddings.env", [])
    mock_window.core.config.set("llama.idx.embeddings.args", [{"name": "model", "value": "EMB-DEF"}])

    openai_emb = MagicMock()
    openai_emb.init_embeddings = MagicMock()
    openai_emb.get_embeddings_model = MagicMock(return_value="OPENAI_EMB")
    mock_window.core.llm.llms = {"openai": openai_emb}

    llm = Llm(mock_window)
    result = llm.get_embeddings_provider()

    assert result == "OPENAI_EMB"
    openai_emb.init_embeddings.assert_called_once()
    openai_emb.get_embeddings_model.assert_called_once()
    mock_window.core.idx.log.assert_called_with(
        "Embeddings: using global provider: openai, model_name: EMB-DEF"
    )


def test_extract_model_name_from_args_prefers_model_then_model_name(mock_window):
    llm = Llm(mock_window)

    args1 = [
        {"name": "foo", "value": "bar"},
        {"name": "model", "value": "M1"},
        {"name": "model_name", "value": "M2"},
    ]
    assert llm.extract_model_name_from_args(args1) == "M1"

    args2 = [
        {"name": "x", "value": "y"},
        {"name": "model_name", "value": "M3"},
    ]
    assert llm.extract_model_name_from_args(args2) == "M3"

    args3 = [{"name": "x", "value": "y"}]
    assert llm.extract_model_name_from_args(args3) == ""


def test_get_service_context_uses_global_embed_when_auto_embed_false(monkeypatch, mock_window):
    llm = Llm(mock_window)
    fake_model = ModelItem()
    fake_model.provider = "p"

    get_mock = MagicMock(return_value="LLM_OBJ")
    emb_mock = MagicMock(return_value="EMB_GLOBAL")
    monkeypatch.setattr(llm, "get", get_mock)
    monkeypatch.setattr(llm, "get_embeddings_provider", emb_mock)

    llm_obj, emb = llm.get_service_context(model=fake_model, stream=True, auto_embed=False)

    assert llm_obj == "LLM_OBJ"
    assert emb == "EMB_GLOBAL"
    get_mock.assert_called_once_with(model=fake_model, stream=True)
    emb_mock.assert_called_once()


def test_get_service_context_uses_custom_embed_when_auto_embed_true(monkeypatch, mock_window):
    llm = Llm(mock_window)
    fake_model = ModelItem()
    fake_model.provider = "p"

    get_mock = MagicMock(return_value="LLM_OBJ")
    cust_emb_mock = MagicMock(return_value="EMB_CUSTOM")
    monkeypatch.setattr(llm, "get", get_mock)
    monkeypatch.setattr(llm, "get_custom_embed_provider", cust_emb_mock)

    llm_obj, emb = llm.get_service_context(model=fake_model, stream=False, auto_embed=True)

    assert llm_obj == "LLM_OBJ"
    assert emb == "EMB_CUSTOM"
    get_mock.assert_called_once_with(model=fake_model, stream=False)
    cust_emb_mock.assert_called_once_with(model=fake_model)


def test_get_custom_embed_provider_uses_matching_provider_and_includes_api_key(mock_window):
    mock_window.core.idx.log = MagicMock()

    defaults = [
        {"provider": "provEmb", "model": "emb-model-1"},
    ]
    mock_window.core.config.set("llama.idx.embeddings.default", defaults)

    emb_provider = MagicMock()
    emb_provider.get_embeddings_model = MagicMock(return_value="EMB_CUSTOM")
    mock_window.core.llm.llms = {"provEmb": emb_provider}

    mock_window.core.models.prepare_client_args = MagicMock(return_value={"api_key": "KEY123"})

    model = ModelItem()
    model.provider = "provEmb"
    model.id = "MODEL-ID"

    llm = Llm(mock_window)
    result = llm.get_custom_embed_provider(model=model)

    assert result == "EMB_CUSTOM"
    emb_provider.get_embeddings_model.assert_called_once()
    cfg = emb_provider.get_embeddings_model.call_args.kwargs["config"]
    assert {"name": "model_name", "type": "str", "value": "emb-model-1"} in cfg
    assert {"name": "api_key", "type": "str", "value": "KEY123"} in cfg

    mock_window.core.idx.log.assert_any_call("Embeddings: trying to use provEmb, model_name: emb-model-1")


def test_get_custom_embed_provider_ollama_no_api_key_and_uses_model_id_when_empty(mock_window):
    mock_window.core.idx.log = MagicMock()

    defaults = [
        {"provider": "ollama", "model": ""},
    ]
    mock_window.core.config.set("llama.idx.embeddings.default", defaults)

    emb_provider = MagicMock()
    emb_provider.get_embeddings_model = MagicMock(return_value="EMB_OLLAMA")
    mock_window.core.llm.llms = {"ollama": emb_provider}

    mock_window.core.models.prepare_client_args = MagicMock(return_value={"api_key": "IGNORED"})

    model = ModelItem()
    model.provider = "ollama"
    model.id = "llama2"

    llm = Llm(mock_window)
    result = llm.get_custom_embed_provider(model=model)

    assert result == "EMB_OLLAMA"
    cfg = emb_provider.get_embeddings_model.call_args.kwargs["config"]
    assert {"name": "model_name", "type": "str", "value": "llama2"} in cfg
    assert not any(item.get("name") == "api_key" for item in cfg)

    mock_window.core.idx.log.assert_any_call("Embeddings: trying to use ollama, model_name: llama2")


def test_get_custom_embed_provider_fallbacks_to_global_when_not_configured_or_none(mock_window):
    mock_window.core.idx.log = MagicMock()

    mock_window.core.config.set("llama.idx.embeddings.default", [{"provider": "other", "model": "x"}])

    global_emb = MagicMock()
    global_emb_return = "EMB_GLOBAL"
    llm = Llm(mock_window)
    llm.get_embeddings_provider = MagicMock(return_value=global_emb_return)

    mock_window.core.llm.llms = {
        "provX": MagicMock(get_embeddings_model=MagicMock(return_value=None))
    }

    model = ModelItem()
    model.provider = "provX"
    model.id = "idX"

    result = llm.get_custom_embed_provider(model=model)
    assert result == global_emb_return

    mock_window.core.idx.log.assert_any_call(
        f"Embeddings: not configured for {model.provider}. Fallback: using global provider."
    )