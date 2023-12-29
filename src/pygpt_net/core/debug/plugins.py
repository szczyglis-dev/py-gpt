#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #


class PluginsDebug:
    def __init__(self, window=None):
        """
        Plugins debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'plugins'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        # presets
        for key in self.window.core.plugins.plugins:
            prefix = "[{}] ".format(key)
            plugin = self.window.core.plugins.plugins[key]
            self.window.core.debug.add(self.id, '----', '')
            self.window.core.debug.add(self.id, str(key), '')
            self.window.core.debug.add(self.id, prefix + 'ID', str(key))

            if plugin.name is not None:
                self.window.core.debug.add(self.id, prefix + 'name', str(plugin.name))

            if plugin.description is not None:
                self.window.core.debug.add(self.id, prefix + 'description', str(plugin.description))

            if plugin.options is not None:
                for key in plugin.options:
                    opt_prefix = prefix + '[options]' + "[{}] ".format(key)
                    self.window.core.debug.add(self.id, opt_prefix, str(plugin.options[key]))

        self.window.core.debug.end(self.id)
