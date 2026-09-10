#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 10:00:00                  #
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
        Return LlamaIndex OpenAI-compatible provider instance for Perplexity.

        Perplexity Sonar exposes an OpenAI-compatible Chat Completions API, so
        use LlamaIndex OpenAILike instead of the dedicated Perplexity
        integration. This keeps Perplexity decoupled from
        llama-index-llms-perplexity and its LlamaIndex version constraints.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.openai_like import OpenAILike

        cfg = window.core.config
        args = self.parse_args(model.llama_index, window)

        if "api_key" not in args or not args["api_key"]:
            args["api_key"] = cfg.get("api_key_perplexity", "")
        if "model" not in args:
            args["model"] = model.id

        custom_base = cfg.get("api_endpoint_perplexity", "").strip()
        if custom_base and "api_base" not in args:
            args["api_base"] = custom_base

        # Sonar uses the OpenAI-compatible Chat Completions endpoint.
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        if model.ctx and "context_window" not in args:
            args["context_window"] = model.ctx

        # Compatibility with the old dedicated Perplexity integration.
        # OpenAILike forwards provider-specific request fields through
        # additional_kwargs rather than accepting them as constructor fields.
        if "enable_search_classifier" in args:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs.setdefault(
                "enable_search_classifier",
                args.pop("enable_search_classifier"),
            )
            args["additional_kwargs"] = additional_kwargs

        # OpenAILike accepts custom httpx clients, so the existing global
        # proxy/timeout handling can be reused without provider-specific code.
        args_injected = self.inject_llamaindex_http_clients(dict(args), cfg)
        try:
            return OpenAILike(**args_injected)
        except TypeError:
            # Compatibility with older OpenAILike releases that may not accept
            # injected httpx clients.
            return OpenAILike(**args)

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
