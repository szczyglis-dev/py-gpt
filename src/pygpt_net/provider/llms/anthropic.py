#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 09:52:00                  #
# ================================================== #

from typing import List, Dict, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX, MODE_CHAT,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class AnthropicLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AnthropicLLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - ANTHROPIC_API_KEY - API key for Anthropic API
        Required args:
            - model: model name, e.g. claude-3-opus-20240229
            - api_key: API key for Anthropic API
        """
        self.id = "anthropic"
        self.name = "Anthropic"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.anthropic import Anthropic
        class AnthropicWithProxy(Anthropic):
            def __init__(self, *args, proxy: str = None, **kwargs):
                super().__init__(*args, **kwargs)
                if not proxy:
                    return

                # sync
                from anthropic import DefaultHttpxClient
                self._client = self._client.with_options(
                    http_client=DefaultHttpxClient(proxy=proxy)
                )

                # async
                import httpx
                try:
                    async_http = httpx.AsyncClient(proxy=proxy)  # httpx >= 0.28
                except TypeError:
                    async_http = httpx.AsyncClient(proxies=proxy)  # httpx <= 0.27

                self._aclient = self._aclient.with_options(http_client=async_http)

        args = self.parse_args(model.llama_index, window)
        proxy = window.core.config.get("api_proxy", None)
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_anthropic", "")

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
        self._merge_anthropic_beta_header(
            args,
            self._remote_tool_beta_headers(args.get("tools") or []),
        )

        return AnthropicWithProxy(**args, proxy=proxy)

    @staticmethod
    def _remote_tool_beta_headers(tools: List[dict]) -> List[str]:
        """Return Anthropic beta headers required by provider-native tools.

        Native Chat computes the same feature flags before choosing the beta
        Messages API. LlamaIndex uses the regular ``messages.create`` path, so
        both Chat with files and Agents v2 must pass the equivalent flags through
        the client's default headers.
        """
        betas = []
        for tool in tools or []:
            if not isinstance(tool, dict):
                continue
            tool_type = str(tool.get("type") or "")
            beta = None
            if tool_type == "computer_20250124":
                beta = "computer-use-2025-01-24"
            elif tool_type == "computer_20251124":
                beta = "computer-use-2025-11-24"
            elif tool_type.startswith("web_fetch_"):
                beta = "web-fetch-2025-09-10"
            elif tool_type.startswith("code_execution_"):
                beta = "code-execution-2025-08-25"
            elif tool_type in {
                "tool_search_tool_regex_20251119",
                "tool_search_tool_bm25_20251119",
            }:
                beta = "advanced-tool-use-2025-11-20"
            elif tool_type == "mcp_toolset":
                beta = "mcp-client-2025-11-20"
            if beta and beta not in betas:
                betas.append(beta)
        return betas

    @staticmethod
    def _merge_anthropic_beta_header(args: dict, betas: List[str]) -> None:
        if not betas:
            return
        headers = args.get("default_headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        else:
            headers = dict(headers)
        current = str(headers.get("anthropic-beta") or "")
        merged = [part.strip() for part in current.split(",") if part.strip()]
        for beta in betas:
            if beta not in merged:
                merged.append(beta)
        headers["anthropic-beta"] = ",".join(merged)
        args["default_headers"] = headers

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """Return Anthropic configured for Agents v2.

        Unlike plain LlamaIndex chat, the agent adapter owns Anthropic's
        client-side Computer Use continuation and preserves the beta headers
        required by legacy Computer Use tool versions.
        """
        from pygpt_net.provider.llms.anthropic_agent import AgentAnthropic

        args = self.parse_args(model.llama_index, window)
        proxy = window.core.config.get("api_proxy", None)
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_anthropic", "")

        built_remote_tools = []
        if allow_remote_tools:
            try:
                built_remote_tools = window.core.api.anthropic.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                window.core.debug.log(e)
                built_remote_tools = []

        if built_remote_tools:
            existing = args.get("tools") or []
            if not isinstance(existing, list):
                existing = []

            def _key(tool: dict) -> str:
                return f"{tool.get('type')}::{tool.get('name')}"

            index = {_key(tool) for tool in existing if isinstance(tool, dict)}
            for tool in built_remote_tools:
                key = _key(tool) if isinstance(tool, dict) else None
                if key and key not in index:
                    existing.append(tool)
                    index.add(key)
            args["tools"] = existing

        self._merge_anthropic_beta_header(
            args,
            self._remote_tool_beta_headers(args.get("tools") or []),
        )
        return AgentAnthropic(**args, proxy=proxy)

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
        from .voyage import VoyageEmbeddingWithProxy
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if "api_key" in args:
            args["voyage_api_key"] = args.pop("api_key")
        if "voyage_api_key" not in args or args["voyage_api_key"] == "":
            args["voyage_api_key"] = window.core.config.get("api_key_voyage", "")
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        timeout = window.core.config.get("api_native_voyage.timeout")
        max_retries = window.core.config.get("api_native_voyage.max_retries")
        proxy = window.core.config.get("api_proxy")
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = ""
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