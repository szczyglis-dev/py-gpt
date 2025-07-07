#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

from .analyzer import Analyzer

class Vision:
    def __init__(self, window=None):
        """
        Audio analyzer

        :param window: Window instance
        """
        self.window = window
        self.analyzer = Analyzer(window)