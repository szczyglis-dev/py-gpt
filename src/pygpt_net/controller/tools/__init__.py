#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.07 23:00:00                  #
# ================================================== #

from pygpt_net.core.tabs.tab import Tab

class Tools:
    def __init__(self, window=None):
        """
        Tools controller

        :param window: Window instance
        """
        self.window = window
        self.tab_tools = {
            'tools.files': ['files', 'folder_filled', Tab.TAB_FILES],
            'tools.calendar': ['calendar', 'calendar', Tab.TAB_TOOL_CALENDAR],
            'tools.notepad': ['notepad', 'paste', Tab.TAB_NOTEPAD],
            'tools.painter': ['painter', 'brush', Tab.TAB_TOOL_PAINTER],
        }

    def setup(self):
        """Setup tools"""
        pass

    def reload(self):
        """Reload tools"""
        pass

    def open_tab(self, type: int):
        """
        Open first tab by type

        :param type: tab type
        """
        idx = self.window.core.tabs.get_min_idx_by_type(type)
        if idx is not None:
            self.window.controller.ui.tabs.switch_tab_by_idx(idx)

    def get_tab_tools(self) -> dict:
        """
        Get tab tools

        :return: tab tools
        """
        return self.tab_tools
