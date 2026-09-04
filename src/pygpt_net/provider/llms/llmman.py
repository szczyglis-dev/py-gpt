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

import os
from typing import Optional, List, Dict

from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.provider.llms.ollama import OllamaLLM


class LlmmanLLM(OllamaLLM):
    """llmman - local model runner serving the Ollama API on port 17434: https://github.com/llmmanorg/llmman"""
    def __init__(self, *args, **kwargs):
        super(LlmmanLLM, self).__init__(*args, **kwargs)
        self.id = "llmman"
        self.name = "llmman"

    @staticmethod
    def get_base_url() -> str:
        """
        Get llmman API base URL (override with LLMMAN_HOST = [host][:port])

        :return: llmman API base URL
        """
        host = os.environ.get("LLMMAN_HOST", "").strip()
        if "://" in host:
            return host.rstrip("/")
        name, _, port = host.rpartition(":") if ":" in host else (host, "", "")
        return f"http://{name or 'localhost'}:{port or 17434}"

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return provider instance for embeddings (Ollama embeddings against the llmman URL)

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        base_url = [{"name": "base_url", "value": self.get_base_url(), "type": "str"}]
        return super().get_embeddings_model(window, base_url + (config or []))

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider (via /v1/models, for the model importer)

        :param window: window instance
        :return: list of models
        """
        client = self.get_client(window)
        return [{"id": item.id, "name": item.id} for item in client.models.list().data]
