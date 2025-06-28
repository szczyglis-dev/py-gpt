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

from typing import Dict, List

from pygpt_net.provider.core.mode.json_file import JsonFileProvider
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)


class Modes:

    def __init__(self, window=None):
        """
        Modes core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.initialized = False
        self.all = [
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_ASSISTANT,
            MODE_AUDIO,
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_EXPERT,
            MODE_IMAGE,
            # MODE_LANGCHAIN,
            MODE_LLAMA_INDEX,
            MODE_VISION,
            MODE_RESEARCH,
        ]
        self.items = {}

    def get_by_idx(self, idx) -> str:
        """
        Return mode by index

        :param idx: index of mode
        :return: mode name
        """
        modes = self.get_all()
        return list(modes.keys())[idx]

    def get_idx_by_name(self, name) -> int:
        """
        Return mode index by name

        :param name: mode name
        :return: mode index
        """
        modes = self.get_all()
        return list(modes.keys()).index(name)

    def get_all(self) -> Dict[str, List[str]]:
        """
        Return modes

        :return: Dict with modes
        """
        return self.items

    def get_default(self) -> str:
        """
        Return default mode name

        :return: default mode name
        """
        for id in self.items:
            if self.items[id].default:
                return id

    def get_next(self, mode: str) -> str:
        """
        Return next mode

        :param mode: current mode
        :return: next mode
        """
        modes = self.get_all()
        keys = list(modes.keys())
        idx = keys.index(mode)
        if idx + 1 < len(keys):
            return keys[idx + 1]
        return keys[0]

    def get_prev(self, mode: str) -> str:
        """
        Return previous mode

        :param mode: current mode
        :return: previous mode
        """
        modes = self.get_all()
        keys = list(modes.keys())
        idx = keys.index(mode)
        if idx - 1 >= 0:
            return keys[idx - 1]
        return keys[-1]

    def load(self):
        """Load modes"""
        self.items = self.provider.load()

    def save(self):
        """Save modes"""
        self.provider.save(self.items)
