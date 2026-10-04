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

from typing import List, Dict, Optional, TYPE_CHECKING

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

from .agents import AnthropicAgents
from .parameters import AnthropicParameters



class AnthropicLLM(BaseLLM):
    agents_class = AnthropicAgents

    def __init__(self, *args, **kwargs):
        super(AnthropicLLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - ANTHROPIC_API_KEY - API key for Anthropic API
        Required args:
            - model: model name, e.g. claude-3-opus-20240229
            - api_key: API key for Anthropic API
        """
        self.parameters = AnthropicParameters(self)
        self.id = "anthropic"
        self.name = "Anthropic"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        from .config import setup
        return setup()

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex chat provider

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :param remote_tools: whether to enable remote tools (e.g., web search, computer use)
        :return: LLM provider instance
        """
        from .capture import AnthropicWithProxy


        args, proxy = self.parameters.prepare(window, model)

        # ---------------------------------------------
        # Remote server tools (e.g., web_search_20250305)
        # We forward provider-native server tools via Anthropic "tools" param.
        # This keeps behavior identical to the native SDK configuration.
        # ---------------------------------------------
        built_remote_tools = []
        if remote_tools:
            try:
                # Reuse the same native server-tool builder as normal Anthropic Chat.
                built_remote_tools = window.core.api.anthropic.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                # Do not break if config builder throws; just skip tools
                window.core.debug.log(e)
                built_remote_tools = []

        if built_remote_tools:
            # Merge with any user-supplied 'tools' (avoid duplicates by (type, name))
            existing = args.get("tools") or []
            if isinstance(existing, list):
                def _key(d: dict) -> str:
                    return f"{d.get('type')}::{d.get('name')}"
                index = {_key(t): True for t in existing if isinstance(t, dict)}
                for t in built_remote_tools:
                    k = _key(t) if isinstance(t, dict) else None
                    if k and k not in index:
                        existing.append(t)
                args["tools"] = existing
            else:
                # Defensive: if 'tools' was something unexpected, overwrite safely
                args["tools"] = list(built_remote_tools)

        # LlamaIndex calls Anthropic's regular ``messages.create`` endpoint.
        # Legacy provider-native tools (notably Computer Use on Claude 4.x) still
        # require their matching ``anthropic-beta`` feature header. Normal Chat
        # computes this in the native Anthropic provider, so mirror it here too.
        # Stable toolsets such as ``computer_toolset_20260801`` intentionally do
        # not add a beta header.
        self.parameters.beta_headers(
            args,
            self.parameters.tool_beta_headers(args.get("tools") or []),
        )
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        self.parameters.reasoning(args, reasoning_effort)

        self.log_llama_create(window, model, args, "AnthropicWithProxy", {"proxy": proxy})
        return AnthropicWithProxy(**args, proxy=proxy)

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return LlamaIndex completion provider without server-side chat tools."""
        return self.llama(
            window=window,
            model=model,
            stream=stream,
            remote_tools=False,
        )

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
        from pygpt_net.provider.llms.voyage.embedding import VoyageEmbeddingWithProxy
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
                or window.core.llm.get_config("voyage", "api_key", "")
            )
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")

        timeout = args.pop("timeout", self.get_embeddings_timeout(window.core.config))
        max_retries = window.core.llm.get_config("voyage", "max_retries")
        proxy = window.core.config.get("api_proxy")
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = ""
        self.log_llama_create(
            window, None, args, "VoyageEmbeddingWithProxy",
            {"proxy": proxy, "timeout": timeout, "max_retries": max_retries},
            kind="embeddings",
        )
        return VoyageEmbeddingWithProxy(
            **args,
            proxy=proxy,
            timeout=timeout,
            max_retries=max_retries,
        )

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider

        :param window: window instance
        :return: list of models
        """
        items = []
        try:
            model = ModelItem()
            model.provider = "anthropic"
            client = window.core.api.anthropic.get_client(MODE_CHAT, model)
            models_list = client.models.list()
            if models_list.data:
                for item in models_list.data:
                    items.append({
                        "id": item.id,
                        "name": item.id,
                    })
        except Exception as e:
            window.core.debug.log(e)
        return items
