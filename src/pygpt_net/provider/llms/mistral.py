#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 01:00:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class MistralAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(MistralAILLM, self).__init__(*args, **kwargs)
        self.id = "mistral_ai"
        self.name = "Mistral AI"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.mistralai import MistralAI
        class MistralAIWithProxy(MistralAI):
            def __init__(self, *args, proxy: Optional[str] = None, **kwargs):
                endpoint = kwargs.get("endpoint")
                super().__init__(*args, **kwargs)
                if not proxy:
                    return

                import httpx
                from mistralai import Mistral
                timeout = getattr(self, "timeout", 120)

                try:
                    sync_client = httpx.Client(proxy=proxy, timeout=timeout, follow_redirects=True)
                    async_client = httpx.AsyncClient(proxy=proxy, timeout=timeout, follow_redirects=True)
                except TypeError:
                    sync_client = httpx.Client(proxies=proxy, timeout=timeout, follow_redirects=True)
                    async_client = httpx.AsyncClient(proxies=proxy, timeout=timeout, follow_redirects=True)

                sdk_kwargs = {
                    "api_key": self.api_key,
                    "client": sync_client,
                    "async_client": async_client,
                }
                if endpoint:
                    sdk_kwargs["server_url"] = endpoint

                self._client = Mistral(**sdk_kwargs)

        args = self.parse_args(model.llama_index, window)
        proxy = window.core.config.get("api_proxy") or None
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_mistral", "")
        return MistralAIWithProxy(**args, proxy=proxy)

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return provider instance for embeddings

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        from llama_index.embeddings.mistralai import MistralAIEmbedding
        class MistralAIEmbeddingWithProxy(MistralAIEmbedding):
            def __init__(self, *args, proxy: Optional[str] = None, api_key: Optional[str] = None, **kwargs):
                captured_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
                super().__init__(*args, api_key=api_key, **kwargs)

                if not proxy:
                    return

                import httpx
                try:
                    sync_client = httpx.Client(proxy=proxy, timeout=60.0, follow_redirects=True)
                    async_client = httpx.AsyncClient(proxy=proxy, timeout=60.0, follow_redirects=True)
                except TypeError:
                    sync_client = httpx.Client(proxies=proxy, timeout=60.0, follow_redirects=True)
                    async_client = httpx.AsyncClient(proxies=proxy, timeout=60.0, follow_redirects=True)

                from mistralai import Mistral
                server_url = os.environ.get("MISTRAL_ENDPOINT") or None
                self._client = Mistral(
                    api_key=captured_key,
                    client=sync_client,
                    async_client=async_client,
                    **({"server_url": server_url} if server_url else {}),
                )
                if hasattr(self, "_mistralai_client"):
                    self._mistralai_client = self._client
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_mistral", "")
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        proxy = window.core.config.get("api_proxy") or None
        return MistralAIEmbeddingWithProxy(**args, proxy=proxy)

    def init_embeddings(
            self,
            window,
            env: Optional[List[Dict]] = None
    ):
        """
        Initialize embeddings provider

        :param window: window instance
        :param env: ENV configuration list
        """
        super(MistralAILLM, self).init_embeddings(window, env)

        # === FIX FOR LOCAL EMBEDDINGS ===
        # if there is no OpenAI api key then set fake key to prevent empty key Llama-index error
        if ('OPENAI_API_KEY' not in os.environ
                and (window.core.config.get('api_key') is None or window.core.config.get('api_key') == "")):
            os.environ['OPENAI_API_KEY'] = "_"

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider

        :param window: window instance
        :return: list of models
        """
        items = []
        client = self.get_client(window)
        models_list = client.models.list()
        if models_list.data:
            for item in models_list.data:
                id = item.id
                items.append({
                    "id": id,
                    "name": id,
                })
        return items
