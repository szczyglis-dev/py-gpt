#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 12:30:00                  #
# ================================================== #

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


class CustomLLM(BaseLLM):
    """Runtime OpenAI Chat Completions-compatible provider."""

    def __init__(
            self,
            provider_id: str,
            name: str,
            api_base: str,
            api_key: str = "",
    ):
        super(CustomLLM, self).__init__()
        self.id = provider_id
        self.name = name
        self.api_base = api_base
        self.api_key = api_key or ""
        self.type = [MODE_LLAMA_INDEX]
        self.is_runtime_custom = True

    def get_api_key(self) -> str:
        """Return configured API key or a harmless SDK placeholder for no-auth endpoints."""
        return self.api_key or "custom"

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
    ) -> LlamaBaseLLM:
        """Return LlamaIndex OpenAILike wrapper for Chat with Files/agents."""
        from llama_index.llms.openai_like import OpenAILike

        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args:
            args["api_key"] = self.get_api_key()
        if "api_base" not in args:
            args["api_base"] = self.api_base
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        if model.ctx and "context_window" not in args:
            args["context_window"] = model.ctx

        # Per-model credentials, when set, still have the highest priority.
        custom_api_key = (getattr(model, "custom_api_key", "") or "").strip()
        custom_api_endpoint = (getattr(model, "custom_api_endpoint", "") or "").strip()
        if custom_api_key:
            args["api_key"] = custom_api_key
        if custom_api_endpoint:
            args["api_base"] = custom_api_endpoint

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAILike(**args)
