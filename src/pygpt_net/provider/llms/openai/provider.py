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
    MODE_CHAT,
    MODE_EMBEDDINGS,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem

from .agents import OpenAIAgents
from .parameters import OpenAIParameters


class OpenAILLM(BaseLLM):
    agents_class = OpenAIAgents

    def __init__(self, *args, **kwargs):
        super(OpenAILLM, self).__init__(*args, **kwargs)
        self.parameters = OpenAIParameters(self)
        self.id = "openai"
        self.name = "OpenAI"
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
        from llama_index.llms.openai import OpenAI as LlamaOpenAI
        if self.get_config("responses_api_llama", False) and window.core.config.get("mode") == MODE_LLAMA_INDEX:
            return self.agents.responses(window, model, stream, mode=MODE_LLAMA_INDEX)
        args = self.prepare_openai_compatible_args(window, model)
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.parameters.chat_reasoning(window, model, args)
        self.log_llama_create(window, model, args, "llama_index.llms.openai.OpenAI")
        return LlamaOpenAI(**args)

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return an OpenAI LlamaIndex adapter for PyGPT Completion mode.

        LlamaIndex exposes ``complete`` / ``stream_complete`` for both legacy
        completion models and chat models. ``OpenAILike`` is used deliberately
        here so newly released OpenAI model IDs do not depend on LlamaIndex's
        hard-coded OpenAI model registry.
        """
        from .completion import OpenAICompletion


        args = self.prepare_openai_compatible_args(window, model)
        model_id = str(args.get("model") or model.id or "").strip()
        if model_id.startswith("text-davinci"):
            # Preserve PyGPT's historical compatibility fallback.
            model_id = "gpt-3.5-turbo-instruct"
        if not model_id:
            raise ValueError("Model name is required for OpenAI completion.")
        args["model"] = model_id

        organization = str(self.get_config("organization", "") or "").strip()
        if organization:
            headers = dict(args.get("default_headers") or {})
            headers.setdefault("OpenAI-Organization", organization)
            args["default_headers"] = headers

        if "context_window" not in args:
            ctx_size = int(getattr(model, "ctx", 0) or 0)
            if ctx_size > 0:
                args["context_window"] = ctx_size

        # A model configured for Chat in PyGPT uses /v1/chat/completions even
        # though the UI mode is Completion. OpenAI's legacy instruct model is
        # completion-only and must always use /v1/completions. Force this value
        # instead of using setdefault(), because old/user LlamaIndex overrides or
        # runtime mode normalization may otherwise leave is_chat_model=True.
        if model_id == "gpt-3.5-turbo-instruct":
            args["is_chat_model"] = False
            args["is_function_calling_model"] = False
        else:
            args.setdefault("is_chat_model", model.has_mode(MODE_CHAT))
            args.setdefault("is_function_calling_model", False)

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAICompletion")
        return OpenAICompletion(**args)

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
        from llama_index.embeddings.openai import OpenAIEmbedding
        args = self.prepare_openai_compatible_embedding_args(window, config)
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        self.log_llama_create(
            window, None, args, "OpenAIEmbedding",
            kind="embeddings",
        )
        return OpenAIEmbedding(**args)
