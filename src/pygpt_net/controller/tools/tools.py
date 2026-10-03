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

from typing import Dict, List, Optional

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
            'tools.calendar': ['calendar', 'calendar', Tab.TAB_TOOL_CALENDAR],
        }

    def setup(self):
        """Setup tools"""
        pass

    def reload(self):
        """Reload tools"""
        pass

    def _confirm_sandbox_rebuild(self, dialog_type: str):
        self.window.ui.dialogs.confirm(
            type=dialog_type,
            id="",
            msg=trans("confirm.tools.sandbox.rebuild"),
            modal=True,
        )

    def rebuild_ipython_docker(self, force: bool = False):
        if not force:
            self._confirm_sandbox_rebuild("tools.sandbox.rebuild.ipython_docker")
            return
        self.window.core.plugins.get("cmd_code_interpreter").builder.build_and_restart()

    def rebuild_python_legacy_docker(self, force: bool = False):
        if not force:
            self._confirm_sandbox_rebuild("tools.sandbox.rebuild.python_legacy_docker")
            return
        self.window.core.plugins.get("cmd_code_interpreter").docker.build_and_restart()

    def rebuild_system_docker(self, force: bool = False):
        if not force:
            self._confirm_sandbox_rebuild("tools.sandbox.rebuild.system_docker")
            return
        self.window.core.plugins.get("cmd_system").docker.build_and_restart()

    def rebuild_python_builtin(self, force: bool = False):
        if not force:
            self._confirm_sandbox_rebuild("tools.sandbox.rebuild.python_builtin")
            return
        self.window.core.plugins.get("cmd_code_interpreter").rebuild_builtin_sandbox()

    def rebuild_system_builtin(self, force: bool = False):
        if not force:
            self._confirm_sandbox_rebuild("tools.sandbox.rebuild.system_builtin")
            return
        self.window.core.plugins.get("cmd_system").rebuild_builtin_sandbox()

    def open_tab(self, type: int):
        """
        Open first tab by type

        :param type: tab type
        """
        idx = self.window.core.tabs.get_min_idx_by_type(type)
        if idx is not None:
            self.window.controller.tabs.switch_tab_by_idx(idx)

    def append_tab_menu(
            self,
            parent: QTabWidget,
            menu: QMenu,
            idx: int,
            column_idx: int,
            caller: QTabWidget = None
    ) -> Optional[QMenu]:
        """
        Append tab menu

        :param parent: parent widget
        :param menu: menu
        :param idx: tab index
        :param column_idx: column index
        :param caller: caller widget (default: None)
        :return: tab add submenu, or None when no tools can be added
        """
        submenu = None
        tools = self.window.tools.get_all()
        if hasattr(parent, 'add_tab'):
            caller = parent
        available = {id: tool for id, tool in tools.items() if tool.can_add_tab()}
        for tool in available.values():
            hook = getattr(tool, 'get_tab_menu', None)
            if hook is not None:
                for action in hook(menu, idx, column_idx, caller):
                    menu.addAction(action)
        for id, tool in available.items():
            if getattr(tool, 'hide_in_tab_tools', False):
                continue
            # Do not offer an action that cannot create anything. Single-instance
            # tools (e.g. Canvas, Agent Workflow and Python/OS) disappear from
            # Add tool as soon as their application-wide tab already exists.
            if submenu is None:
                submenu = menu.addMenu(QIcon(":/icons/add.svg"), trans("action.tab.add.tool"))
            icon = tool.tab_icon
            title = trans(tool.tab_title)
            action = QAction(QIcon(icon), title, parent)
            action.triggered.connect(
                lambda checked=False, idx=idx, column_idx=column_idx, id=id, caller=caller: caller.add_tab(idx, column_idx, Tab.TAB_TOOL, id)
            )
            submenu.addAction(action)
        return submenu

    def get_tab_tools(self) -> Dict[str, List[str]]:
        """
        Get tab tools

        :return: tab tools
        """
        return self.tab_tools
