#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 12:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.provider.llms.llmman import LlmmanLLM as Wrapper


def test_ids():
    wrapper = Wrapper()
    assert wrapper.id == "llmman"
    assert wrapper.name == "llmman"


def test_get_base_url():
    with patch.dict("os.environ", {}, clear=True):
        assert Wrapper.get_base_url() == "http://localhost:17434"
    with patch.dict("os.environ", {"LLMMAN_HOST": "0.0.0.0:18000"}):
        assert Wrapper.get_base_url() == "http://0.0.0.0:18000"
    with patch.dict("os.environ", {"LLMMAN_HOST": "myhost"}):
        assert Wrapper.get_base_url() == "http://myhost:17434"
    with patch.dict("os.environ", {"LLMMAN_HOST": ":18000"}):
        assert Wrapper.get_base_url() == "http://localhost:18000"


def test_get_embeddings_model(mock_window):
    wrapper = Wrapper()
    with patch("llama_index.embeddings.ollama.OllamaEmbedding") as embedding, \
            patch.dict("os.environ", {"OLLAMA_API_BASE": "http://ollama:11434"}, clear=True):
        wrapper.get_embeddings_model(mock_window, [{"name": "model", "value": "gemma4", "type": "str"}])
        kwargs = embedding.call_args.kwargs
        assert kwargs["model_name"] == "gemma4"
        assert kwargs["base_url"] == "http://localhost:17434"


def test_get_models(mock_window):
    wrapper = Wrapper()
    client = MagicMock()
    client.models.list.return_value.data = [MagicMock(id="gemma4"), MagicMock(id="qwen3.8")]
    wrapper.get_client = MagicMock(return_value=client)
    assert wrapper.get_models(mock_window) == [
        {"id": "gemma4", "name": "gemma4"},
        {"id": "qwen3.8", "name": "qwen3.8"},
    ]
