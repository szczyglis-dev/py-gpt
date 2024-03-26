# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from .base import BaseTool

class Tools:
    def __init__(self, window=None):
        """
        Tools manager

        :param window: Window instance
        """
        self.window = window
        self.tools = {}

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

    def setup(self):
        """Setup tools"""
        for id in self.tools:
            self.tools[id].setup()

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

    def setup_menu_actions(self) -> dict:
        """
        Setup Tools menu actions

        :return: dict with menu actions
        """
        actions = {}
        for id in self.tools:
            tmp_actions = self.tools[id].setup_menu()
            if tmp_actions and isinstance(tmp_actions, list):
                if id not in actions:
                    actions[id] = []
                actions[id] += tmp_actions
        return actions
        
