#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Dict, List

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QTabWidget, QMenu

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


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

    def append_tab_menu(
            self,
            parent: QTabWidget,
            menu: QMenu,
            idx: int,
            column_idx: int
    ) -> QMenu:
        """
        Append tab menu

        :param parent: parent widget
        :param menu: menu
        :param idx: tab index
        :param column_idx: column index
        :return: tab add submenu
        """
        submenu = menu.addMenu(QIcon(":/icons/add.svg"), trans("action.tab.add.tool"))
        tools = self.window.tools.get_all()
        for id in tools:
            tool = tools[id]
            if not tool.has_tab:
                continue
            icon = tool.tab_icon
            title = trans(tool.tab_title)
            action = QAction(QIcon(icon), title, parent)
            action.triggered.connect(
                lambda idx=idx, column_idx=column_idx, id=id: parent.add_tab(idx, column_idx, Tab.TAB_TOOL, id)
            )
            submenu.addAction(action)
        return submenu

    def get_tab_tools(self) -> Dict[str, List[str]]:
        """
        Get tab tools

        :return: tab tools
        """
        return self.tab_tools
