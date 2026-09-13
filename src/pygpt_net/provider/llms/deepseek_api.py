#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 12:00:00                  #
# ================================================== #

from typing import List, Dict, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class DeepseekApiLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(DeepseekApiLLM, self).__init__(*args, **kwargs)
        self.id = "deepseek_api"
        self.name = "Deepseek API"
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
        from pygpt_net.provider.llms.llama_index.deepseek import DeepSeek
        args = self.prepare_openai_compatible_args(window, model)
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return DeepSeek(**args)

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
        if not args.get("voyage_api_key"):
            args["voyage_api_key"] = (
                self.get_env_override(
                    window,
                    window.core.config.get("llama.idx.embeddings.env", []) or [],
                    ["VOYAGE_API_KEY"],
                )
                or window.core.config.get("api_key_voyage", "")
            )
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")

        timeout = args.pop("timeout", self.get_embeddings_timeout(window.core.config))
        max_retries = window.core.config.get("api_native_voyage.max_retries")
        proxy = window.core.config.get("api_proxy")
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = ""
        return VoyageEmbeddingWithProxy(
            **args,
            proxy=proxy,
            timeout=timeout,
            max_retries=max_retries,
        )
