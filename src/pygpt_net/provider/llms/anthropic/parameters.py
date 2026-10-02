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

from typing import Optional, List


class AnthropicParameters:
    def __init__(self, provider):
        self.provider = provider

    # ========================================
    # Model configuration
    # ========================================

    def prepare(self, window, model):
        args = self.provider.parse_args(model.llama_index, window)
        proxy = window.core.config.get("api_proxy", None)
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = None
        if not args.get("model"):
            args["model"] = model.id
        if not args.get("api_key"):
            args["api_key"] = (
                self.provider.get_env_override(
                    window,
                    (model.llama_index or {}).get("env", []),
                    ["ANTHROPIC_API_KEY"],
                )
                or self.provider.get_config("api_key", "")
            )
        return args, proxy

    # ========================================
    # Reasoning
    # ========================================

    @staticmethod
    def reasoning(args: dict, reasoning_effort: Optional[str]) -> None:
        """Forward Anthropic effort without requiring a new SDK signature.

        PyGPT currently supports anthropic==0.75.0. Its stable
        ``Messages.create`` method does not declare ``output_config`` even
        though the API accepts the field. LlamaIndex forwards
        ``additional_kwargs`` directly to that method, so putting
        ``output_config`` there raises ``unexpected keyword argument``.
        ``extra_body`` is supported by that SDK and is merged into the JSON
        request body, which also keeps this compatible with newer SDKs.
        """
        if not reasoning_effort:
            return
        additional_kwargs = dict(args.get("additional_kwargs") or {})
        extra_body = dict(additional_kwargs.get("extra_body") or {})
        output_config = dict(extra_body.get("output_config") or {})
        output_config["effort"] = reasoning_effort
        extra_body["output_config"] = output_config
        additional_kwargs["extra_body"] = extra_body
        args["additional_kwargs"] = additional_kwargs

    # ========================================
    # Remote tools
    # ========================================

    @staticmethod
    def tool_beta_headers(tools: List[dict]) -> List[str]:
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
    def beta_headers(args: dict, betas: List[str]) -> None:
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
