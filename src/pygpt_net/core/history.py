#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from pygpt_net.core.provider.history.txt_file import TxtFileProvider


class History:

    def __init__(self, window):
        """
        History handler

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "txt_file"
        self.path = None

        # register data providers
        self.add_provider(TxtFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add data provider

        :param provider: data provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def install(self):
        """Install provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].install()
            except Exception as e:
                self.window.app.debug.log(e)

    def append(self, ctx, mode):
        """
        Append text to history

        :param ctx: CtxItem instance
        :param mode: mode (input | output)
        """
        if self.provider in self.providers:
            try:
                self.providers[self.provider].append(ctx, mode)
            except Exception as e:
                if self.window is not None:
                    self.window.app.debug.log(e)
                else:
                    print("Error appending to history: {}".format(e))
