#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 19:00:00                  #
# ================================================== #

from .openai import OpenAIRemoteStore
from .google import GoogleRemoteStore

class RemoteStore:
    def __init__(self, window=None):
        """
        Assistant controller

        :param window: Window instance
        """
        self.window = window
        self.openai = OpenAIRemoteStore(window)
        self.google = GoogleRemoteStore(window)