#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
# ================================================== #

from .actions import Actions
from .helpers import Helpers
from .shortcuts import Shortcuts
from .voice import Voice

class Access:
    def __init__(self, window=None):
        """
        Accessibility core

        :param window: Window instance
        """
        self.window = window
        self.actions = Actions(window)
        self.helpers = Helpers(window)
        self.shortcuts = Shortcuts(window)
        self.voice = Voice(window)

        