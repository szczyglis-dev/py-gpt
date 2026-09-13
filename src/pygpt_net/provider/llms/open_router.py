#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 19:00:00                  #
# ================================================== #

from typing import Optional, Dict, List

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class OpenRouterLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OpenRouterLLM, self).__init__(*args, **kwargs)
        self.id = "open_router"
        self.name = "OpenRouter"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

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
        from llama_index.embeddings.openai_like import OpenAILikeEmbedding
        args = self.prepare_openai_compatible_embedding_args(window, config)
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        return OpenAILikeEmbedding(**args)

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
        from llama_index.llms.openai_like import OpenAILike
        args = self.prepare_openai_compatible_args(window, model)
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            # OpenRouter uses its own top-level ``reasoning`` object, while the
            # pinned OpenAI SDK validates Chat Completions keyword arguments.
            # ``extra_body`` is the supported escape hatch for provider-specific
            # OpenRouter fields and LlamaIndex forwards it to the OpenAI client.
            extra_body = dict(additional_kwargs.get("extra_body") or {})
            reasoning = dict(extra_body.get("reasoning") or {})
            reasoning["effort"] = reasoning_effort
            extra_body["reasoning"] = reasoning
            additional_kwargs["extra_body"] = extra_body
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        if model:
            args["model"] = window.core.models.get_openrouter_model(model)
        return OpenAILike(**args)