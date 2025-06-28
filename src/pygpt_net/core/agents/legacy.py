#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

from typing import List

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_AUDIO,
    MODE_RESEARCH,
)

class Legacy:
    def __init__(self, window=None):
        """
        Agents core (legacy)

        :param window: Window instance
        """
        self.window = window
        self.allowed_modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_VISION,
            # MODE_LANGCHAIN,
            MODE_LLAMA_INDEX,
            MODE_AUDIO,
            MODE_RESEARCH,
        ]

    def get_allowed_modes(self) -> List[str]:
        """
        Get allowed modes

        :return: allowed modes
        """
        return self.allowed_modes

    def get_mode(self) -> str:
        """
        Get sub-mode to use internally

        :return: sub-mode
        """
        mode = MODE_CHAT
        current = self.window.core.config.get("agent.mode")
        if current is not None and current in self.allowed_modes:
            mode = current
        return mode

    def get_idx(self) -> str:
        """
        Get agent index

        :return: agent index
        """
        return self.window.core.config.get("agent.idx")