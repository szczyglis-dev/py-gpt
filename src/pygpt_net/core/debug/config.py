#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
# ================================================== #

import os


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

        path = os.path.join(self.window.config.path, '', 'config.json')
        self.window.debugger.add(self.id, 'Config File', str(path))

        # config data
        for key in self.window.config.all():
            self.window.debugger.add(self.id, key, str(self.window.config.get(key)))

        self.window.debugger.end(self.id)
