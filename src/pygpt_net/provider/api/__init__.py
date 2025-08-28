#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 09:00:00                  #
# ================================================== #

from .anthropic import ApiAnthropic
from .openai import ApiOpenAI

class Api:

    def __init__(self, window=None):
        """
        API wrappers core

        :param window: Window instance
        """
        self.window = window
        self.anthropic = ApiAnthropic(window)
        self.openai = ApiOpenAI(window)