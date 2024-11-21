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

from .common import Common
from .experts import Experts
from .legacy import Legacy
from .llama import Llama

class Agent:
    def __init__(self, window=None):
        """
        Agent controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.experts = Experts(window)
        self.llama = Llama(window)
        self.legacy = Legacy(window)

    def setup(self):
        """Setup agent controller"""
        self.legacy.setup()
        self.llama.setup()

    def reload(self):
        """Reload agent toolbox options"""
        self.legacy.reload()
        self.llama.reload()

    def stop(self):
        """Force stop all agents"""
        self.legacy.on_stop()
        self.llama.on_stop()
