#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

from .loaders import Loaders

class UI:
    def __init__(self, window=None):
        """
        UI components

        :param window: Window instance
        """
        self.window = window
        self.loaders = Loaders(window)