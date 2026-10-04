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

from typing import TYPE_CHECKING, Optional, Dict, List


if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_EMBEDDINGS,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class LocalLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(LocalLLM, self).__init__(*args, **kwargs)
        self.id = "local_ai"
        self.name = "Local model (OpenAI API compatible)"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        return {"openai_compatible": True}

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
        from llama_index.llms.openai_like import OpenAILike
        args = self.prepare_openai_compatible_args(window, model)
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

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
        from llama_index.embeddings.openai_like import OpenAILikeEmbedding
        args = self.prepare_openai_compatible_embedding_args(window, config)
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        self.log_llama_create(
            window, None, args, "OpenAILikeEmbedding",
            kind="embeddings",
        )
        return OpenAILikeEmbedding(**args)
