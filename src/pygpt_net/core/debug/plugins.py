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

        # plugins
        for key in self.window.core.plugins.plugins:
            plugin = self.window.core.plugins.plugins[key]
            data = {
                'id': plugin.id,
            }
            if plugin.name is not None:
                data['name'] = plugin.name
            if plugin.description is not None:
                data['description'] = plugin.description
            if plugin.options is not None:
                data['options'] = plugin.options
            self.window.core.debug.add(self.id, str(key), str(data))

        self.window.core.debug.end(self.id)
