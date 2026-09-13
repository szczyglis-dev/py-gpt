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
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        if not args.get("model"):
            args["model"] = model.id
        if not args.get("api_key"):
            args["api_key"] = (
                self.get_env_override(
                    window,
                    (model.llama_index or {}).get("env", []),
                    ["MISTRAL_API_KEY"],
                )
                or window.core.config.get("api_key_mistral", "")
            )
        if not args.get("endpoint"):
            endpoint = (
                self.get_env_override(
                    window,
                    (model.llama_index or {}).get("env", []),
                    ["MISTRAL_ENDPOINT"],
                )
                or window.core.config.get("api_endpoint_mistral", "")
            )
            if endpoint:
                args["endpoint"] = endpoint
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
            def __init__(
                    self,
                    *args,
                    proxy: Optional[str] = None,
                    api_key: Optional[str] = None,
                    endpoint: Optional[str] = None,
                    timeout: Optional[float] = None,
                    **kwargs
            ):
                captured_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
                super().__init__(*args, api_key=api_key, **kwargs)

                # The upstream embedding wrapper does not expose a custom
                # endpoint. Rebuild its SDK client when PyGPT has one so the
                # normal global provider endpoint is honored without requiring
                # an Advanced ENV entry.
                server_url = endpoint or os.environ.get("MISTRAL_ENDPOINT") or None
                from mistralai import Mistral
                sdk_kwargs = {"api_key": captured_key}
                if timeout is not None:
                    sdk_kwargs["timeout_ms"] = int(timeout * 1000)
                if server_url:
                    sdk_kwargs["server_url"] = server_url

                if proxy:
                    import httpx
                    http_timeout = timeout if timeout is not None else 60.0
                    try:
                        sync_client = httpx.Client(proxy=proxy, timeout=http_timeout, follow_redirects=True)
                        async_client = httpx.AsyncClient(proxy=proxy, timeout=http_timeout, follow_redirects=True)
                    except TypeError:
                        sync_client = httpx.Client(proxies=proxy, timeout=http_timeout, follow_redirects=True)
                        async_client = httpx.AsyncClient(proxies=proxy, timeout=http_timeout, follow_redirects=True)
                    sdk_kwargs["client"] = sync_client
                    sdk_kwargs["async_client"] = async_client

                self._client = Mistral(**sdk_kwargs)
                if hasattr(self, "_mistralai_client"):
                    self._mistralai_client = self._client
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if not args.get("api_key"):
            args["api_key"] = (
                self.get_env_override(
                    window,
                    window.core.config.get("llama.idx.embeddings.env", []) or [],
                    ["MISTRAL_API_KEY"],
                )
                or window.core.config.get("api_key_mistral", "")
            )
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")
        if not args.get("endpoint"):
            endpoint = (
                self.get_env_override(
                    window,
                    window.core.config.get("llama.idx.embeddings.env", []) or [],
                    ["MISTRAL_ENDPOINT"],
                )
                or window.core.config.get("api_endpoint_mistral", "")
            )
            if endpoint:
                args["endpoint"] = endpoint

        proxy = window.core.config.get("api_proxy") or None
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        args.setdefault("timeout", self.get_embeddings_timeout(window.core.config))
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

        # Local embeddings must not write a fake OPENAI_API_KEY into the global
        # environment, as that would leak into subsequent OpenAI API calls.
        # The Mistral embedding provider does not require an OpenAI key.
