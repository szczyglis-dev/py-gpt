#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.18 17:30:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
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
            MODE_AGENT_OPENAI,
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
        """Compatibility shim for the removed standalone Vision mode.

        Inline image requests are routed at request time by the Vision plugin.
        The UI mode is intentionally not changed here.
        """
        return

    def allowed(self) -> bool:
        """
        Check if vision content is allowed

        :return: True if allowed
        """
        return self.window.controller.plugins.is_enabled('openai_vision') or self.is_vision_model()

    def is_vision_model(self) -> bool:
        """
        Check if current model is vision model

        :return: True if vision model
        """
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_data = self.window.core.models.get(model)
        if model_data:
            return model_data.is_image_input() and mode in self.allowed_modes
        return False

