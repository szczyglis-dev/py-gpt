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

"""Anthropic agent adapter construction and Computer Use selection."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pygpt_net.item.model import ModelItem

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from ..agents import ProviderAgents


class AnthropicAgents(ProviderAgents):
    # ========================================
    # Agent adapters
    # ========================================

    def create(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True,
            force_computer_use: bool = False,
    ) -> LlamaBaseLLM:
        """Return Anthropic configured for Agents v2.

        Unlike plain LlamaIndex chat, the agent adapter owns Anthropic's
        client-side Computer Use continuation and preserves the beta headers
        required by legacy Computer Use tool versions.
        """
        from .agent import AgentAnthropic

        args, proxy = self.provider.parameters.prepare(window, model)

        built_remote_tools = []
        if force_computer_use:
            try:
                if window.core.api.anthropic.computer.supports_model(model):
                    built_remote_tools = [window.core.api.anthropic.computer.get_tool(model=model)]
            except Exception as e:
                window.core.debug.log(e)
                built_remote_tools = []
        elif allow_remote_tools:
            try:
                built_remote_tools = window.core.api.anthropic.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                window.core.debug.log(e)
                built_remote_tools = []

        if built_remote_tools:
            if force_computer_use:
                # Dedicated Computer Use mirrors native MODE_COMPUTER behavior:
                # keep the provider Computer tool exclusive.
                args["tools"] = built_remote_tools
            else:
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

        self.provider.parameters.beta_headers(
            args,
            self.provider.parameters.tool_beta_headers(args.get("tools") or []),
        )
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        self.provider.parameters.reasoning(args, reasoning_effort)
        self.provider.log_llama_create(window, model, args, "AgentAnthropic", {"proxy": proxy})
        return AgentAnthropic(**args, proxy=proxy)

    # ========================================
    # Computer Use
    # ========================================

    def computer_enabled(self, window, model, stream=False, force_computer_use=False):
        try:
            if force_computer_use and window.core.api.anthropic.computer.supports_model(model):
                remote_tools = [window.core.api.anthropic.computer.get_tool(model=model)]
            else:
                remote_tools = window.core.api.anthropic.remote_tools.build_remote_tools(model=model) or []
        except Exception as exc:
            window.core.debug.log(exc)
            remote_tools = []
        computer_types = {
            "computer_20250124",
            "computer_20251124",
            "computer_toolset_20260801",
        }
        return any(
                isinstance(tool, dict) and str(tool.get("type") or "") in computer_types
                for tool in remote_tools
        )
