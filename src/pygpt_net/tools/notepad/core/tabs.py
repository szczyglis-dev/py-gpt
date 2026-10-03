#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Navigation and titles for generic Notepad tool tabs."""
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans

class Tabs:
    def __init__(self, tool):
        self.tool = tool
        self.opened_once = False

    def all(self):
        return self.tool.window.controller.tabs.get_tabs_by_tool(self.tool.id)

    def count(self):
        return len(self.all())

    def is_active(self):
        tab = self.tool.window.controller.tabs.get_current_tab()
        return tab is not None and tab.type == Tab.TAB_TOOL and tab.tool_id == self.tool.id

    def current(self):
        tab = self.tool.window.controller.tabs.get_first_tab_by_tool(self.tool.id)
        return tab.data_id if tab is not None else 1

    def open(self, idx=None):
        controller = self.tool.window.controller.tabs
        tab = (controller.get_first_tab_by_tool(self.tool.id) if idx is None else
               next((tab for tab in self.all() if tab.data_id == idx), None))
        if tab is not None:
            self.tool.window.controller.tabs.activate_tab(tab)
        elif idx is not None and self.tool.storage.get_by_id(idx) is not None:
            controller = self.tool.window.controller.tabs
            tab = controller.append(type=Tab.TAB_TOOL, tool_id=self.tool.id, idx=-2,
                                    column_idx=controller.get_current_column_idx(), data_id=idx)
        else:
            tab = self.tool.open_tab()
        self.tool.window.activateWindow()
        return tab

    def next_title(self):
        suffix = sum(bool(tab.title) for tab in self.all())
        for tab in self.all():
            try:
                suffix = max(suffix, int((tab.title or '').rsplit(' ', 1)[-1]))
            except (ValueError, IndexError):
                pass
        return trans(self.tool.tab_title) + ' ' + str(suffix + 1)

    def close_all(self, column_idx):
        for tab in tuple(self.all()):
            if tab.column_idx == column_idx:
                self.tool.window.controller.tabs.close(tab.idx, column_idx)
