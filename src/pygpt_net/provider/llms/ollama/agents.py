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

"""Ollama agent adapter construction and Computer Use selection."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pygpt_net.item.model import ModelItem

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from ..agents import ProviderAgents


class OllamaAgents(ProviderAgents):
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
        """Build the native Ollama LlamaIndex adapter used by tool loops."""
        from .custom import Ollama

        args = self.provider.parameters.native(window, model)
        self.provider.log_llama_create(window, model, args, "llama_index.llms.ollama.Ollama")
        return Ollama(**args)
