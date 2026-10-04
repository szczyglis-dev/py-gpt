#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_EMBEDDINGS,
)

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class MistralAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(MistralAILLM, self).__init__(*args, **kwargs)
        self.id = "mistral_ai"
        self.name = "Mistral AI"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        from .config import setup
        return setup()

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex chat provider

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from .chat import MistralAIWithProxy

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
                or self.get_config("api_key", "")
            )
        if not args.get("endpoint"):
            endpoint = (
                self.get_env_override(
                    window,
                    (model.llama_index or {}).get("env", []),
                    ["MISTRAL_ENDPOINT"],
                )
                or self.get_config("api_base", "")
            )
            if endpoint:
                args["endpoint"] = endpoint
        self.log_llama_create(window, model, args, "MistralAIWithProxy", {"proxy": proxy})
        return MistralAIWithProxy(**args, proxy=proxy)

    def llama_embeddings(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return LlamaIndex embeddings provider

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        from .embedding import MistralAIEmbeddingWithProxy
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
                or self.get_config("api_key", "")
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
                or self.get_config("api_base", "")
            )
            if endpoint:
                args["endpoint"] = endpoint

        proxy = window.core.config.get("api_proxy") or None
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        args.setdefault("timeout", self.get_embeddings_timeout(window.core.config))
        self.log_llama_create(
            window, None, args, "MistralAIEmbeddingWithProxy",
            {"proxy": proxy},
            kind="embeddings",
        )
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
