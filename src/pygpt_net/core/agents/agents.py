#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from .custom import Custom
from .legacy import Legacy
from .observer import Observer
from .provider import Provider
from .tools import Tools

class Agents:
    def __init__(self, window=None):
        """
        Agents core

        :param window: Window instance
        """
        self.window = window
        self.custom = Custom(window)
        self.legacy = Legacy(window)
        self._memory = None
        self.observer = Observer(window)
        self.provider = Provider(window)
        self._runner = None
        self.tools = Tools(window)

    @property
    def memory(self):
        """Create LlamaIndex-backed legacy agent memory only when used."""
        if self._memory is None:
            from .memory import Memory
            self._memory = Memory(self.window)
        return self._memory

    @property
    def runner(self):
        """Create legacy agent runners only for an actual legacy agent request."""
        if self._runner is None:
            from .runner import Runner
            self._runner = Runner(self.window)
        return self._runner
