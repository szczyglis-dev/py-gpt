# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import Dict, Optional

from PySide6.QtGui import QAction

from pygpt_net.ui.widget.dialog.base import BaseDialog
from .base import BaseTool

class Tools:
    def __init__(self, window=None):
        """
        Tools manager

        :param window: Window instance
        """
        self.window = window
        self.tools = {}
        self.initialized = False

    def register(self, tool: BaseTool):
        """
        Register tool

        :param tool: Tool instance
        """
        self.tools[tool.id] = tool
        self.tools[tool.id].attach(self.window)

    def get(self, id: str) -> BaseTool:
        """
        Get tool instance by ID

        :param id: tool ID
        :return tool instance
        """
        if id in self.tools:
            return self.tools[id]

    def get_all(self) -> Dict[str, BaseTool]:
        """
        Get all tools

        :return: dict with tools
        """
        return self.tools

    def setup(self):
        """Setup tools"""
        self.setup_dialogs()
        for id in self.tools:
            self.tools[id].setup()
        self.setup_theme()
        self.initialized = True

    def post_setup(self):
        """Post-setup, after plugins are loaded"""
        for id in self.tools:
            self.tools[id].post_setup()

    def on_update(self):
        """On app main loop update"""
        for id in self.tools:
            self.tools[id].on_update()

    def on_post_update(self):
        """On app main loop post update"""
        for id in self.tools:
            self.tools[id].on_post_update()

    def on_exit(self):
        """On app exit"""
        for id in self.tools:
            self.tools[id].on_exit()

    def on_reload(self):
        """On app profile reload"""
        for id in self.tools:
            self.tools[id].on_reload()

    def setup_menu_actions(self) -> Dict[str, QAction]:
        """
        Setup Tools menu actions

        :return: dict with menu actions
        """
        actions = {}
        for id in self.tools:
            tool_actions = self.tools[id].setup_menu()
            if tool_actions and isinstance(tool_actions, dict):
                for id in tool_actions:
                    key = "tools." + id
                    actions[key] = tool_actions[id]
        return actions

    def setup_dialogs(self):
        """Setup dialogs"""
        for id in self.tools:
            self.tools[id].setup_dialogs()

    def setup_theme(self):
        """Setup theme"""
        if not self.initialized:
            return
        for id in self.tools:
            self.tools[id].setup_theme()

    def get_instance(
            self,
            type_id: str,
            dialog_id: Optional[str] = None
    ) -> Optional[BaseDialog]:
        """
        Spawn and return dialog instance

        :param type_id: dialog instance type ID
        :param dialog_id: dialog instance ID
        :return: BaseDialog instance or None
        """
        for id in self.tools:
            instance = self.tools[id].get_instance(type_id, dialog_id)
            if instance is not None:
                return instance

    def get_lang_mappings(self) -> Dict[str, dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        mappings = {}
        for id in self.tools:
            tool_mappings = self.tools[id].get_lang_mappings()
            if tool_mappings and isinstance(tool_mappings, dict):
                for key in tool_mappings:
                    if key not in mappings:
                        mappings[key] = tool_mappings[key]
                    else:
                        mappings[key].update(tool_mappings[key])
        return mappings
        
