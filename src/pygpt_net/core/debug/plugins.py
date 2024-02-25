#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 22:00:00                  #
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

        plugins = list(self.window.core.plugins.plugins.keys())
        for key in plugins:
            plugin = self.window.core.plugins.plugins[key]
            data = {
                'id': plugin.id,
                'name': plugin.name,
                'description': plugin.description,
                'options': plugin.options
            }
            self.window.core.debug.add(self.id, str(key), str(data))

        self.window.core.debug.end(self.id)
