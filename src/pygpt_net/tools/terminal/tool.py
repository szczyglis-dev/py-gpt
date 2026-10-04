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
"""Terminal integration with the application's tool and surface APIs."""
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool, ToolMenuAction, ToolToolbarItem
from pygpt_net.utils import trans
from .ui.widget import TerminalWidget
from .ui.dialog import TerminalDialog


class Terminal(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'terminal'
        self.allow_tab = self.allow_dialog = True
        self.multi_tab = True
        self.hide_in_tab_tools = True
        self.dialog_id = 'terminal'
        self.on_menu_click = ToolMenuAction.ALWAYS_DIALOG
        self.tab_title = 'output.tab.terminal'
        self.tab_icon = ':/icons/terminal.svg'
        self.widgets = []

    def new_frontend(self, parent=None):
        widget = TerminalWidget(self, parent)
        self.widgets.append(widget)
        return widget

    def as_tab(self, tab):
        widget = self.new_frontend()
        widget.set_tab(tab)
        self.register_surface(widget, widget, tab=tab)
        return widget

    def open(self):
        dialog = self.window.ui.dialog.get(self.dialog_id)
        if dialog is None:
            dialog = TerminalDialog(self)
            self.window.ui.dialog[self.dialog_id] = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.widget.setFocus()
        return dialog

    def on_selected(self, tab):
        for widget in self.widgets:
            if widget.tab is tab:
                widget.focus_terminal()
                QTimer.singleShot(0, widget.focus_terminal)
                break

    def get_toolbar(self):
        return [ToolToolbarItem(self.tab_icon, self.tab_title,
                lambda: self.window.controller.toolbar.toggle_tool(Tab.TAB_TOOL, self.id))]

    def get_tab_menu(self, parent, idx, column_idx, caller):
        action = QAction(QIcon(self.tab_icon), trans('action.tab.add.terminal'), parent)
        action.triggered.connect(lambda checked=False: caller.add_tab(idx, column_idx, Tab.TAB_TOOL, self.id))
        return [action]

    def setup_menu(self):
        action = QAction(QIcon(self.tab_icon), trans(self.tab_title), self.window)
        action.triggered.connect(self.on_menu_action)
        self.add_lang_mapping(action, self.tab_title)
        return {self.id: action}

    def setup_theme(self):
        size = self.window.core.config.get('terminal.font_size', self.window.core.config.get('font_size'))
        if isinstance(size, (int, float)):
            for widget in self.widgets:
                widget.apply_font(size)

    def on_exit(self):
        for widget in list(self.widgets):
            widget.on_delete()
