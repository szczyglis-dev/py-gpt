#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

class Agents:
    def __init__(self, window=None):
        """
        Agents core

        :param window: Window instance
        """
        self.window = window
        self.allowed_modes = ["chat", "completion", "vision", "langchain", "llama_index"]

    def get_allowed_modes(self) -> list:
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
        mode = "chat"
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