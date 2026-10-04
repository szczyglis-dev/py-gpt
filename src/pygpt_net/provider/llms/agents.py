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

"""Agent adapter construction, separate from provider configuration and chat."""

from __future__ import annotations


class ProviderAgents:
    def __init__(self, provider):
        self.provider = provider

    # ========================================
    # Agent adapters
    # ========================================

    def create(self, window, model, stream=False, allow_remote_tools=True, force_computer_use=False):
        """Providers without a native agent adapter reuse their regular model."""
        return self.provider.llama(window=window, model=model, stream=stream)

    # ========================================
    # Computer Use
    # ========================================

    def bind_computer_use(self, window, model, stream=False, computer_runtime=None, force_computer_use=False):
        """Bind the continuation adapter only when Computer Use is selected."""
        if not self.computer_enabled(window, model, stream, force_computer_use):
            return self.provider.llama(window=window, model=model, stream=stream)
        llm = self.create(window=window, model=model, stream=stream,
                          allow_remote_tools=True, force_computer_use=force_computer_use)
        binder = getattr(llm, "bind_computer_runtime", None)
        if callable(binder):
            binder(computer_runtime)
        return llm

    def computer_enabled(self, window, model, stream=False, force_computer_use=False):
        return False
