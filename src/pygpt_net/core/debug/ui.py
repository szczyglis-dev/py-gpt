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


class UIDebug:
    def __init__(self, window=None):
        """
        UI debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'ui'

    def map_structure(self, d, show_value: bool = False):
        """
        Map dict structure

        :param d: data to map
        :param show_value: show value
        :return: mapped structure
        """
        if isinstance(d, dict):
            return {k: self.map_structure(v, show_value) for k, v in d.items()}
        elif isinstance(d, list):
            return [self.map_structure(item, show_value) for item in d]
        else:
            if show_value:
                return d
            else:
                return type(d).__name__

    def update_section(self, items: dict, name: str):
        """
        Update debug items

        :param items: items
        :param name: name
        """
        self.window.core.debug.add(self.id, 'ui.' + name, str(self.map_structure(items)))

    def update(self):
        """Update debug window"""
        self.window.core.debug.begin(self.id)

        self.window.core.debug.add(
            self.id, '*lang_mapping',
            str(self.map_structure(self.window.controller.lang.mapping.get_mapping(), True))
        )

        self.update_section(self.window.ui.config, 'config')
        self.update_section(self.window.ui.debug, 'debug')
        self.update_section(self.window.ui.dialog, 'dialog')
        self.update_section(self.window.ui.editor, 'editor')
        self.update_section(self.window.ui.groups, 'groups')
        self.update_section(self.window.ui.hooks, 'hooks')
        self.update_section(self.window.ui.menu, 'menu')
        self.update_section(self.window.ui.models, 'models')
        self.update_section(self.window.ui.nodes, 'nodes')
        self.update_section(self.window.ui.notepad, 'notepad')
        self.update_section(self.window.ui.paths, 'paths')
        self.update_section(self.window.ui.plugin_addon, 'plugin_addon')
        self.update_section(self.window.ui.splitters, 'splitters')
        self.update_section(self.window.ui.tabs, 'tabs')

        self.window.core.debug.end(self.id)
