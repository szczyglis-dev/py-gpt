#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT LlamaIndex LLM-provider tutorial             #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from typing import Dict, List, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


class ExampleLlm(BaseLLM):
    """Example LlamaIndex LLM + embeddings wrapper.

    The launcher `llms=` registry is used by PyGPT's LlamaIndex subsystem. It is
    not the native Chat-mode transport. Normal Chat uses the model's configured
    API provider/OpenAI-compatible endpoint directly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_llm"  # model.provider must match this ID
        self.name = "Example LlamaIndex provider"
        self.description = "Tutorial provider backed by LlamaIndex OpenAI classes."
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def llama(
        self,
        window,
        model: ModelItem,
        stream: bool = False,
    ) -> LlamaBaseLLM:
        """Return the LlamaIndex LLM instance for the selected PyGPT model."""

        # `model.llama_index` contains the per-model ENV/kwargs edited in the
        # Models Editor. Passing `window` lets BaseLLM expand config placeholders
        # such as `{api_key}` inside string values.
        args = self.parse_args(model.llama_index, window)

        # A provider should normally supply a model name when the user has not
        # explicitly provided one in the advanced LlamaIndex kwargs.
        args.setdefault("model", model.id)

        # Use the global key as a fallback for this OpenAI-backed tutorial.
        # Provider-specific implementations should use their own config keys.
        if "api_key" not in args:
            args["api_key"] = window.core.config.get("api_key", "")

        # Current ModelItem supports per-model API credentials. If your backend
        # can use them, non-empty custom values should have highest priority.
        custom_api_key = (model.custom_api_key or "").strip()
        custom_api_endpoint = (model.custom_api_endpoint or "").strip()
        if custom_api_key:
            args["api_key"] = custom_api_key
        if custom_api_endpoint:
            args["api_base"] = custom_api_endpoint

        # PyGPT centralizes proxy-aware sync/async httpx clients in BaseLLM.
        # Use this helper for LlamaIndex providers that accept these arguments.
        args = self.inject_llamaindex_http_clients(args, window.core.config)

        return LlamaOpenAI(**args)

    def get_embeddings_model(
        self,
        window,
        config: Optional[List[Dict]] = None,
    ) -> BaseEmbedding:
        """Return an embedding model for this provider."""
        args = {}
        if config:
            args = self.parse_args({"args": config}, window)

        # OpenAIEmbedding expects `model_name`; PyGPT configs often use `model`.
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        args.setdefault("api_key", window.core.config.get("api_key", ""))
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAIEmbedding(**args)

    # Optional extension point:
    # def get_models(self, window) -> List[Dict]:
    #     """Return [{"id": "model-id", "name": "Display name"}, ...]
    #     if you want the Models importer to query this provider dynamically.
    #     """
    #     return []
