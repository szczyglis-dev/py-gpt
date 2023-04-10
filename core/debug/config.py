#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

class ConfigDebug:
    def __init__(self, window=None):
        """
        Config debug

        :param window: main window object
        """
        self.window = window
        self.id = 'config'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        # config data
        for key in self.window.config.data:
            self.window.debugger.add(self.id, key, str(self.window.config.data[key]))

        self.window.debugger.end(self.id)
