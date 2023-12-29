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


class UIDebug:
    def __init__(self, window=None):
        """
        UI debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'ui'

    def update_section(self, items, name):
        """Update debug items"""
        self.window.core.debug.add(self.id, 'ui.' + name, '')

        for key in sorted(dict(items).keys()):
            prefix = " -- ".format(key)
            self.window.core.debug.add(self.id, prefix, str(key))

    def update(self):
        """Update debug window"""
        self.window.core.debug.begin(self.id)

        self.update_section(self.window.ui.config_option, 'config_option')
        self.update_section(self.window.ui.debug, 'debug')
        self.update_section(self.window.ui.dialog, 'dialog')
        self.update_section(self.window.ui.editor, 'editor')
        self.update_section(self.window.ui.groups, 'groups')
        self.update_section(self.window.ui.menu, 'menu')
        self.update_section(self.window.ui.models, 'models')
        self.update_section(self.window.ui.nodes, 'nodes')
        self.update_section(self.window.ui.notepad, 'notepad')
        self.update_section(self.window.ui.paths, 'paths')
        self.update_section(self.window.ui.plugin_addon, 'plugin_addon')
        self.update_section(self.window.ui.plugin_data, 'plugin_data')
        self.update_section(self.window.ui.plugin_option, 'plugin_option')
        self.update_section(self.window.ui.splitters, 'splitters')
        self.update_section(self.window.ui.tabs, 'tabs')

        self.window.core.debug.end(self.id)
