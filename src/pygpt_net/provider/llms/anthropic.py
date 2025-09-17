#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 20:00:00                  #
# ================================================== #

from typing import List, Dict, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX, MODE_CHAT,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class AnthropicLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AnthropicLLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - ANTHROPIC_API_KEY - API key for Anthropic API
        Required args:
            - model: model name, e.g. claude-3-opus-20240229
            - api_key: API key for Anthropic API
        """
        self.id = "anthropic"
        self.name = "Anthropic"
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
        from llama_index.llms.anthropic import Anthropic
        class AnthropicWithProxy(Anthropic):
            def __init__(self, *args, proxy: str = None, **kwargs):
                super().__init__(*args, **kwargs)
                if not proxy:
                    return

                # sync
                from anthropic import DefaultHttpxClient
                self._client = self._client.with_options(
                    http_client=DefaultHttpxClient(proxy=proxy)
                )

                # async
                import httpx
                try:
                    async_http = httpx.AsyncClient(proxy=proxy)  # httpx >= 0.28
                except TypeError:
                    async_http = httpx.AsyncClient(proxies=proxy)  # httpx <= 0.27

                self._aclient = self._aclient.with_options(http_client=async_http)

        args = self.parse_args(model.llama_index, window)
        proxy = window.core.config.get("api_proxy", None)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_anthropic", "")

        # ---------------------------------------------
        # Remote server tools (e.g., web_search_20250305)
        # We forward provider-native server tools via Anthropic "tools" param.
        # This keeps behavior identical to the native SDK configuration.
        # ---------------------------------------------
        try:
            remote_tools = window.core.api.anthropic.tools.build_remote_tools(model=model) or []
        except Exception as e:
            # Do not break if config builder throws; just skip tools
            window.core.debug.log(e)
            remote_tools = []

        if remote_tools:
            # Merge with any user-supplied 'tools' (avoid duplicates by (type, name))
            existing = args.get("tools") or []
            if isinstance(existing, list):
                def _key(d: dict) -> str:
                    return f"{d.get('type')}::{d.get('name')}"
                index = {_key(t): True for t in existing if isinstance(t, dict)}
                for t in remote_tools:
                    k = _key(t) if isinstance(t, dict) else None
                    if k and k not in index:
                        existing.append(t)
                args["tools"] = existing
            else:
                # Defensive: if 'tools' was something unexpected, overwrite safely
                args["tools"] = list(remote_tools)

        return AnthropicWithProxy(**args, proxy=proxy)

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
        from .voyage import VoyageEmbeddingWithProxy
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if "api_key" in args:
            args["voyage_api_key"] = args.pop("api_key")
        if "voyage_api_key" not in args or args["voyage_api_key"] == "":
            args["voyage_api_key"] = window.core.config.get("api_key_voyage", "")
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        timeout = window.core.config.get("api_native_voyage.timeout")
        max_retries = window.core.config.get("api_native_voyage.max_retries")
        proxy = window.core.config.get("api_proxy")
        return VoyageEmbeddingWithProxy(
            **args,
            proxy=proxy,
            timeout=timeout,
            max_retries=max_retries,
        )

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider

        :param window: window instance
        :return: list of models
        """
        model = ModelItem()
        model.provider = "anthropic"
        client = window.core.api.anthropic.get_client(MODE_CHAT, model)
        models_list = client.models.list()
        items = []
        if models_list.data:
            for item in models_list.data:
                items.append({
                    "id": item.id,
                    "name": item.id,
                })
        return items