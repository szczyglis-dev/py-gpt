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

"""Native Ollama endpoint and request options shared by completion and agents."""

from pygpt_net.core.types import MODE_CHAT


class OllamaParameters:
    def __init__(self, provider):
        self.provider = provider

    # ========================================
    # Model configuration
    # ========================================

    def native(self, window, model, function_calling=True):
        args = self.provider.parse_args(model.llama_index, window)
        model_id = (model.get_ollama_model() or model.id or "").strip()
        if not model_id:
            raise ValueError("Ollama model name is required")

        # Resolve the same configured endpoint as normal Chat, then convert the
        # OpenAI-compatible /v1 base back to Ollama's native server root.
        client_args = window.core.models.prepare_client_args(MODE_CHAT, model)
        base_url = str(
            client_args.get("base_url") or window.core.models.ollama.get_base_url()
        ).rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3].rstrip("/")

        # model.llama_index args may contain OpenAI/OpenAILike-only options.
        # Keep native Ollama options and normalize common aliases.
        args.pop("api_key", None)
        args.pop("api_base", None)
        args.pop("base_url", None)
        args.pop("is_chat_model", None)
        if "timeout" in args and "request_timeout" not in args:
            args["request_timeout"] = args.pop("timeout")
        args.setdefault("request_timeout", 300.0)
        args["model"] = model_id
        args["base_url"] = base_url
        args["is_function_calling_model"] = bool(function_calling and model.tool_calls)

        ctx_size = window.core.models.get_num_ctx(model.id) if model.id else 0
        if ctx_size <= 0:
            ctx_size = window.core.config.get("max_total_tokens") or 0
        if ctx_size > 0 and "context_window" not in args:
            args["context_window"] = int(ctx_size)

        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            args["think"] = reasoning_effort

        return args
