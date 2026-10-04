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

"""Google agent adapter construction and Computer Use selection."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pygpt_net.item.model import ModelItem

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from ..agents import ProviderAgents
from .parameters import google_types


class GoogleAgents(ProviderAgents):
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
        """Return Google GenAI configured for Agents v2.

        Remote Google tools are merged with FunctionAgent tools at request time
        by the adapter, and grounding URLs are collected for PyGPT artifacts.
        """
        from .agent import AgentGoogleGenAI

        args = self.provider.parameters.prepare(window, model)
        self.provider.parameters.reasoning(window, model, args)

        remote = []
        if force_computer_use:
            try:
                if window.core.api.google.remote_tools.supports_computer_use(model):
                    remote = [window.core.api.google.computer.get_tool()]
            except Exception as e:
                window.core.debug.log(e)
        elif allow_remote_tools:
            try:
                remote = window.core.api.google.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                window.core.debug.log(e)

        if isinstance(args.get("generation_config"), dict):
            args["generation_config"] = google_types().GenerateContentConfig(**args["generation_config"])

        self.provider.log_llama_create(window, model, args, "AgentGoogleGenAI", {"pygpt_remote_tools": remote})
        return AgentGoogleGenAI(
            **args,
            pygpt_remote_tools=remote,
        )

    # ========================================
    # Computer Use
    # ========================================

    def computer_enabled(self, window, model, stream=False, force_computer_use=False):
        remote = window.core.api.google.remote_tools
        computer_enabled = (
            remote.supports_computer_use(model)
            if force_computer_use
            else remote.is_computer_use_enabled(model)
        )
        return computer_enabled
