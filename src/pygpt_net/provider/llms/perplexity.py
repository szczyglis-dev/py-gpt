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

from typing import Optional, List, Dict

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_RESEARCH,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class PerplexityLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(PerplexityLLM, self).__init__(*args, **kwargs)
        self.id = "perplexity"
        self.name = "Perplexity"
        self.type = [MODE_CHAT, MODE_RESEARCH]

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama (Perplexity)

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.perplexity import Perplexity as LlamaPerplexity
        from .utils import ProxyEnv

        cfg = window.core.config
        args = self.parse_args(model.llama_index, window)

        if "api_key" not in args or not args["api_key"]:
            args["api_key"] = cfg.get("api_key_perplexity", "")
        if "model" not in args:
            args["model"] = model.id

        custom_base = cfg.get("api_endpoint_perplexity", "").strip()
        if custom_base and "api_base" not in args:
            args["api_base"] = custom_base

        # httpx.Client/AsyncClient (proxy, timeout, socks etc.)
        try:
            args_injected = self.inject_llamaindex_http_clients(dict(args), cfg)
            return LlamaPerplexity(**args_injected)
        except TypeError:
            return LlamaPerplexity(**args)

        # -----------------------------------
        # TODO: fallback
        proxy = cfg.get("api_proxy") or cfg.get("api_native_perplexity.proxy")
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""

        class PerplexityWithProxy(LlamaPerplexity):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                self._proxy = proxy

            # sync
            def complete(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return super().complete(*a, **kw)

            def chat(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return super().chat(*a, **kw)

            def stream_complete(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return super().stream_complete(*a, **kw)

            def stream_chat(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return super().stream_chat(*a, **kw)

            # async
            async def acomplete(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return await super().acomplete(*a, **kw)

            async def achat(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    return await super().achat(*a, **kw)

            async def astream_complete(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    async for chunk in super().astream_complete(*a, **kw):
                        yield chunk

            async def astream_chat(self, *a, **kw):
                with ProxyEnv(self._proxy):
                    async for chunk in super().astream_chat(*a, **kw):
                        yield chunk

        return PerplexityWithProxy(**args)

    def llama_multimodal(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaMultiModalLLM:
        """
        Return multimodal LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

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
        pass

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
                items.append({
                    "id": item.id,
                    "name": item.id,
                })
        return items
