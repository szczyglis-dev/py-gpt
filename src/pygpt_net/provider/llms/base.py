#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:48:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM

from pygpt_net.core.types import (
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX, 
    MODE_CHAT,
)
from pygpt_net.item.model import ModelItem
from pygpt_net.utils import parse_args


class BaseLLM:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.name = ""
        self.type = []  # langchain, llama_index, embeddings
        self.description = ""

    def init(
            self,
            window,
            model: ModelItem,
            mode: str,
            sub_mode: str = None
    ):
        """
        Initialize provider

        :param window: window instance
        :param model: model instance
        :param mode: mode (langchain, llama_index)
        :param sub_mode: sub mode (chat, completion)
        """
        options = {}
        if mode == MODE_LANGCHAIN:
            pass
            # options = model.langchain
        elif mode == MODE_LLAMA_INDEX:
            options = model.llama_index
        if 'env' in options:
            for item in options['env']:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

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
        if env is not None and len(env) > 0:
            for item in env:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

    def parse_args(
            self,
            options: dict,
            window = None
    ) -> dict:
        """
        Parse extra args

        :param options: LLM options dict (langchain, llama_index)
        :param window: window instance
        :return: parsed arguments dict
        """
        args = {}
        if 'args' in options:
            if options['args'] is not None:
                args = parse_args(options['args'])
                if window:
                    for key in args:
                        if isinstance(args[key], str):
                            try:
                                args[key] = args[key].format(**window.core.config.all())
                            except Exception as e:
                                pass
        return args

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for completion in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for chat in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex LLM instance for plain-text completion.

        Providers may override this when their regular LlamaIndex wrapper maps
        ``complete()`` back to a chat endpoint. The default implementation uses
        the same provider object as Chat with Files and the caller invokes its
        ``complete`` / ``stream_complete`` methods directly.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LlamaIndex LLM provider instance
        """
        return self.llama(window=window, model=model, stream=stream)

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama index query and chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def llama_chat_with_files(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
    ) -> LlamaBaseLLM:
        """Return the regular LlamaIndex LLM for Chat with Files.

        Providers with client-side native tools such as Computer Use may
        override this hook and reuse their provider continuation adapter.
        """
        return self.llama(window=window, model=model, stream=stream)

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex LLM instance for Agents v2.

        Providers with native/server-side remote tools can override this method
        and attach them directly to the LLM request. The default implementation
        simply reuses the regular LlamaIndex provider.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :param allow_remote_tools: allow provider-native remote tools
        :return: provider instance
        """
        return self.llama(window=window, model=model, stream=stream)

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
        :return: provider instance
        """
        pass

    def get_openai_agent_provider(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return agent provider instance for OpenAI agents

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: agent provider instance
        """
        pass

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider.

        The default implementation queries the OpenAI-compatible ``/models``
        endpoint and is safe to call when the endpoint is unreachable: it logs
        the failure and returns an empty list instead of raising. Providers
        with a non-OpenAI schema must override this method.

        :param window: window instance
        :return: list of models
        """
        items: List[Dict] = []
        try:
            client = self.get_client(window)
            models_list = client.models.list()
            if models_list.data:
                items.extend(
                    {"id": item.id, "name": item.id} for item in models_list.data
                )
        except Exception as e:
            window.core.debug.log(e)
        return items

    def get_client(self, window):
        """
        Return client for current provider

        :param window: Window instance
        :return: Client instance for the provider
        """
        model = ModelItem()
        model.provider = self.id
        return window.core.api.openai.get_client(
            mode=MODE_CHAT,
            model=model,
        )

    def inject_llamaindex_http_clients(self, args: dict, cfg) -> dict:
        import httpx
        proxy = (cfg.get("api_proxy") or "").strip()  # e.g. "http://user:pass@host:3128"
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        common_kwargs = dict(timeout=60.0, follow_redirects=True)
        if proxy:
            common_kwargs["proxy"] = proxy  # httpx>=0.28

        args["http_client"] = httpx.Client(**common_kwargs)
        args["async_http_client"] = httpx.AsyncClient(**common_kwargs)
        return args
