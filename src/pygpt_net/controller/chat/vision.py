#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)

class Vision:
    def __init__(self, window=None):
        """
        Chat vision controller

        :param window: Window instance
        """
        self.window = window
        self.is_enabled = False
        self.is_available = False
        self.allowed_modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_LANGCHAIN,
            MODE_LLAMA_INDEX,
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_RESEARCH,
        ]

    def setup(self):
        """Set up UI"""
        pass

    def show_inline(self):
        """Show inline vision checkbox"""
        self.window.ui.nodes['inline.vision'].setVisible(True)  # show vision checkbox

    def hide_inline(self):
        """Hide inline vision checkbox"""
        self.window.ui.nodes['inline.vision'].setVisible(False)  # hide vision checkbox

    def available(self):
        """Set vision content available"""
        self.is_available = True

    def unavailable(self):
        """Set vision content unavailable"""
        self.is_available = False

    def switch_to_vision(self):
        """Switch to vision mode"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)
        if mode in [MODE_AGENT, MODE_AGENT_LLAMA]:
            return  # disallow change in agent modes
        if mode == MODE_CHAT and MODE_VISION in model_data.mode:
            return  # abort if vision is already allowed
        if mode == MODE_VISION:
            return
        # abort if vision is already enabled
        if not self.window.controller.plugins.is_enabled('openai_vision') \
                or (self.window.controller.plugins.is_enabled('openai_vision')
                    and mode not in self.allowed_modes):
            self.window.controller.mode.set(MODE_VISION)

    def allowed(self) -> bool:
        """
        Check if vision content is allowed

        :return: True if allowed
        """
        if self.window.controller.plugins.is_enabled('openai_vision') \
                or self.window.core.config.get('mode') in self.allowed_modes:
            return True
        return False

