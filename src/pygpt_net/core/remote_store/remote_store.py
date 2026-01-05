#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

from .openai import Store as OpenAIStore
from .google import Store as GoogleStore
from .anthropic import Store as AnthropicStore
from .xai import Store as XAIStore

class RemoteStore:
    def __init__(self, window=None):
        """
        Remote vector stores core

        :param window: Window instance
        """
        self.window = window
        self.openai = OpenAIStore(self.window)
        self.google = GoogleStore(self.window)
        self.anthropic = AnthropicStore(self.window)
        self.xai = XAIStore(self.window)