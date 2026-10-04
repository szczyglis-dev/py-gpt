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

"""Shared request parameter policy for chat and agent adapters."""

from __future__ import annotations

from pygpt_net.item.model import ModelItem


from pygpt_net.core.types.reasoning import get_google_thinking_kwargs


def google_types():
    from google.genai import types
    return types


class GoogleParameters:
    def __init__(self, provider):
        self.provider = provider

    # ========================================
    # Model configuration
    # ========================================

    def prepare(self, window, model):
        args = self.provider.parse_args(model.llama_index, window)
        if not args.get("model"):
            model_id = str(model.id or "").strip()
            if model_id and not model_id.startswith("models/"):
                model_id = "models/" + model_id
            args["model"] = model_id
        if not args.get("api_key"):
            args["api_key"] = (
                self.provider.get_env_override(
                    window,
                    (model.llama_index or {}).get("env", []),
                    ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
                )
                or self.provider.get_config("api_key", "")
            )

        window.core.api.google.setup_env()  # setup VertexAI if configured
        args = self.provider.inject_llamaindex_http_clients(args, window.core.config)
        return args

    # ========================================
    # Generation configuration
    # ========================================

    @staticmethod
    def generation_config(value) -> dict:
        """Normalize a Google GenerateContentConfig/dict for safe merging."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        try:
            return value.model_dump(exclude_none=True)
        except Exception:
            return {}

    # ========================================
    # Reasoning
    # ========================================

    def reasoning(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if not effort:
            return
        thinking = get_google_thinking_kwargs(model.id, effort)
        if not thinking:
            return
        generation_config = self.generation_config(args.get("generation_config"))
        # llama-index-llms-google-genai 0.11.1 expects a typed
        # GenerateContentConfig here and calls .model_dump() on it internally.
        generation_config["thinking_config"] = google_types().ThinkingConfig(**thinking)
        args["generation_config"] = google_types().GenerateContentConfig(**generation_config)
