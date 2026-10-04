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

from .agents import OllamaAgents
from .parameters import OllamaParameters



class OllamaLLM(BaseLLM):
    agents_class = OllamaAgents

    def __init__(self, *args, **kwargs):
        super(OllamaLLM, self).__init__(*args, **kwargs)
        self.parameters = OllamaParameters(self)
        self.id = "ollama"
        self.name = "Ollama"
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

        When PyGPT tools are enabled, tool-capable Ollama models must use the
        native ``/api/chat`` protocol. The OpenAI-compatible
        ``/v1/chat/completions`` bridge can return the first tool call correctly,
        but it does not preserve Ollama/Gemma tool state reliably on the follow-up
        request containing the tool result. In Chat with Files this manifested as
        a successfully executed plugin tool followed by an empty model response.

        Plain chat/index calls keep the OpenAILike transport to avoid changing the
        established no-tools path unnecessarily.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        if bool(model.tool_calls) and bool(window.core.config.get("cmd", False)):
            return self.agents.create(window, model, stream=stream)

        import nest_asyncio
        from llama_index.llms.openai_like import OpenAILike

        nest_asyncio.apply()
        args = self.parse_args(model.llama_index, window)

        model_id = (model.get_ollama_model() or model.id or "").strip()
        if not model_id:
            raise ValueError("Ollama model name is required")
        args["model"] = model_id

        # Reuse the exact endpoint/key resolution used by normal Chat,
        # including OLLAMA_API_BASE and per-model custom API overrides.
        client_args = window.core.models.prepare_client_args(MODE_CHAT, model)
        api_base = (client_args.get("base_url") or "").strip()
        if not api_base:
            api_base = window.core.models.ollama.get_base_url().rstrip("/") + "/v1"

        if not args.get("api_key"):
            args["api_key"] = client_args.get("api_key") or "ollama"
        if not args.get("api_base"):
            args["api_base"] = api_base
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        args["is_function_calling_model"] = False
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs

        # Keep PyGPT model limits in LlamaIndex metadata/request settings.
        ctx_size = window.core.models.get_num_ctx(model.id) if model.id else 0
        if ctx_size <= 0:
            ctx_size = window.core.config.get("max_total_tokens") or 0
        if ctx_size > 0 and "context_window" not in args:
            args["context_window"] = int(ctx_size)

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return native Ollama text completion through ``/api/generate``."""
        from .completion import OllamaCompletion

        args = self.parameters.native(window, model, function_calling=False)
        self.log_llama_create(window, model, args, "OllamaCompletion")
        return OllamaCompletion(**args)

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
        from llama_index.embeddings.ollama import OllamaEmbedding
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if not args.get("base_url"):
            # Advanced embedding ENV is an override; otherwise resolve the
            # normal app-level OLLAMA_API_BASE setting. Reading the configured
            # rows directly avoids a stale process ENV value after an override
            # has been cleared in the UI.
            base_url = (
                self.get_env_override(
                    window,
                    window.core.config.get("llama.idx.embeddings.env", []) or [],
                    ["OLLAMA_API_BASE"],
                )
                or self.get_env_override(
                    window,
                    window.core.config.get("app.env", []) or [],
                    ["OLLAMA_API_BASE"],
                )
                or "http://localhost:11434"
            )
            args["base_url"] = base_url
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")
        client_kwargs = dict(args.get("client_kwargs") or {})
        client_kwargs.setdefault("timeout", self.get_embeddings_timeout(window.core.config))
        args["client_kwargs"] = client_kwargs
        self.log_llama_create(
            window, None, args, "OllamaEmbedding", kind="embeddings",
        )
        return OllamaEmbedding(**args)

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
        super(OllamaLLM, self).init_embeddings(window, env)

        # Local embeddings must not write a fake OPENAI_API_KEY into the global
        # environment, as that would leak into subsequent OpenAI API calls.
        # The Ollama embedding provider (llama_embeddings) does not require
        # an OpenAI key, so no injection is needed here.
