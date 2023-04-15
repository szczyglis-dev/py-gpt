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

import os


class PluginsDebug:
    def __init__(self, window=None):
        """
        Plugins debug

        :param window: main window object
        """
        self.window = window
        self.id = 'plugins'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        # presets
        for key in self.window.controller.plugins.handler.plugins:
            prefix = "[{}] ".format(key)
            plugin = self.window.controller.plugins.handler.plugins[key]
            self.window.debugger.add(self.id, prefix + 'ID', str(key))

            if plugin.name is not None:
                self.window.debugger.add(self.id, prefix + 'name', str(plugin.name))

            if plugin.description is not None:
                self.window.debugger.add(self.id, prefix + 'description', str(plugin.description))

            if plugin.options is not None:
                for key in plugin.options:
                    opt_prefix = prefix + '[options]' + "[{}] ".format(key)
                    self.window.debugger.add(self.id, opt_prefix, str(plugin.options[key]))

        self.window.debugger.end(self.id)
