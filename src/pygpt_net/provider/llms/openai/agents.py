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

"""OpenAI agent adapter construction and Computer Use selection."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pygpt_net.item.model import ModelItem
from pygpt_net.core.types import MODE_AGENT_V2, MODE_COMPUTER, MODE_LLAMA_INDEX

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from ..agents import ProviderAgents


class OpenAIAgents(ProviderAgents):
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
        """
        Return OpenAI LLM for Agents v2.

        Provider-native remote tools are attached directly to OpenAI Responses,
        exactly through the same PyGPT remote-tools builder used by normal Chat.
        Local FunctionAgent tools are merged by LlamaIndex at request time.
        """
        return self.responses(
            window, model, stream,
            mode=MODE_COMPUTER if force_computer_use else MODE_AGENT_V2,
            allow_remote_tools=allow_remote_tools,
        )

    def responses(self, window, model, stream=False, mode=MODE_LLAMA_INDEX, allow_remote_tools=True):
        from .responses_agent import AgentOpenAIResponses
        args = self.provider.prepare_openai_compatible_args(window, model)
        args = self.provider.inject_llamaindex_http_clients(args, window.core.config)
        if allow_remote_tools:
            self._remote_tools(window, model, stream, mode, args)
        self.provider.parameters.responses_reasoning(window, model, args)
        self.provider.log_llama_create(window, model, args, "AgentOpenAIResponses")
        llm = AgentOpenAIResponses(**args)
        return window.core.context_manager.configure_llm_for_rolling_context(llm)

    # ========================================
    # Computer Use
    # ========================================

    def computer_enabled(self, window, model, stream=False, force_computer_use=False):
        tools = window.core.api.openai.remote_tools.append_to_tools(
            mode=MODE_COMPUTER if force_computer_use else MODE_LLAMA_INDEX,
            model=model,
            stream=stream,
            is_expert_call=False,
            tools=[],
            preset=None,
        )
        return any(isinstance(tool, dict) and tool.get("type") == "computer" for tool in tools)

    # ========================================
    # Private helpers
    # ========================================

    def _remote_tools(
            self,
            window,
            model: ModelItem,
            stream: bool,
            mode: str,
            args: dict,
    ) -> list:
        """Attach provider-native Responses tools and their artifact includes."""
        tools = window.core.api.openai.remote_tools.append_to_tools(
            mode=mode,
            model=model,
            stream=stream,
            is_expert_call=False,
            tools=[],
            preset=None,
        )
        if tools:
            args["built_in_tools"] = tools
            self.provider.parameters.sources(args, tools)
        return tools
