#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 01:00:00                  #
# ================================================== #


class UIDebug:
    def __init__(self, window=None):
        """
        UI debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'ui'

    def _sortable_key(self, key):
        """
        Return a safe, comparable key representation for sorting across heterogeneous key types.
        Uses str() with robust fallbacks to avoid TypeError.
        """
        try:
            return str(key)
        except Exception:
            try:
                return repr(key)
            except Exception:
                return f"{type(key).__name__}@{id(key)}"

    def _sorted_items(self, d: dict):
        """
        Return dict items sorted by key at this nesting level.
        """
        return sorted(d.items(), key=lambda kv: self._sortable_key(kv[0]))

    def map_structure(self, d, show_value: bool = False):
        """
        Map dict structure

        :param d: data to map
        :param show_value: show value
        :return: mapped structure with keys sorted at every nesting level
        """
        if isinstance(d, dict):
            out = {}
            for k, v in self._sorted_items(d):
                out[k] = self.map_structure(v, show_value)
            return out
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
        self.window.core.debug.add(self.id, f"ui.{name}", str(self.map_structure(items)))

    def update(self):
        """Update debug window"""
        # Local references
        debug = self.window.core.debug
        lang_mapping = self.window.controller.lang.mapping.get_mapping()
        ui = self.window.ui

        debug.begin(self.id)

        debug.add(self.id, '*lang_mapping', str(self.map_structure(lang_mapping, True)))

        # Update sections using local 'ui' reference
        self.update_section(ui.config, 'config')
        self.update_section(ui.debug, 'debug')
        self.update_section(ui.dialog, 'dialog')
        self.update_section(ui.editor, 'editor')
        self.update_section(ui.groups, 'groups')
        self.update_section(ui.hooks, 'hooks')
        self.update_section(ui.menu, 'menu')
        self.update_section(ui.models, 'models')
        self.update_section(ui.nodes, 'nodes')
        self.update_section(ui.notepad, 'notepad')
        self.update_section(ui.paths, 'paths')
        self.update_section(ui.plugin_addon, 'plugin_addon')
        self.update_section(ui.splitters, 'splitters')
        self.update_section(ui.tabs, 'tabs')

        debug.end(self.id)