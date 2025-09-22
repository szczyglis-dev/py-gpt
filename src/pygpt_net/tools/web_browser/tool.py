#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.22 19:00:00                  #
# ================================================== #

from typing import Dict

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool, TabWidget
from pygpt_net.utils import trans

from .ui.dialogs import Tool
from .ui.widgets import ToolSignals


class WebBrowser(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Web Browser tool

        :param window: Window instance
        """
        super(WebBrowser, self).__init__(*args, **kwargs)
        self.id = "web_browser"
        self.dialog_id = "web_browser"
        self.has_tab = True
        self.tab_title = "menu.tools.web_browser"
        self.tab_icon = ":/icons/web_on.svg"
        self.opened = False
        self.is_edit = False
        self.auto_clear = True
        self.dialog = None
        self.is_edit = False
        self.auto_opened = False
        self.signals = ToolSignals()

    def setup(self):
        """Setup"""
        self.update()

    def on_reload(self):
        """On app profile reload"""
        self.setup()

    def update(self):
        """Update menu"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        """
        if self.opened:
            self.window.ui.menu['tools.web_browser'].setChecked(True)
        else:
            self.window.ui.menu['tools.web_browser'].setChecked(False)
        """

    def get_dialog_id(self) -> str:
        """
        Get dialog ID

        :return: Dialog ID
        """
        return self.dialog_id

    def set_url(self, url: str):
        """
        Set output URL

        :param url: URL to load
        """
        self.signals.url.emit(url)

    def open(self, load: bool = True):
        """
        Open HTML canvas dialog

        :param load: Load output data
        """
        if not self.opened:
            self.opened = True
            self.auto_opened = False
            self.window.ui.dialogs.open(self.dialog_id, width=800, height=600)
            self.dialog.widget.on_open()
            self.update()

    def auto_open(self, load: bool = True):
        """
        Auto open canvas dialog or tab

        :param load: Load output data
        """
        if self.window.controller.ui.tabs.is_current_tool(self.id):
            tool_col = self.window.controller.ui.tabs.get_tool_column(self.id)
            current_col = self.window.controller.ui.tabs.column_idx
            if tool_col == 1 and tool_col != current_col:
                self.window.controller.ui.tabs.enable_split_screen(True)  # enable split screen
            return # do not open if already opened in tab
        elif self.window.controller.ui.tabs.is_tool(self.id):
            tab = self.window.controller.ui.tabs.get_first_tab_by_tool(self.id)
            if tab:
                tool_col = tab.column_idx
                current_col = self.window.controller.ui.tabs.column_idx
                self.window.controller.ui.tabs.switch_tab_by_idx(tab.idx, tab.column_idx)
                if tool_col == 1 and tool_col != current_col:
                    self.window.controller.ui.tabs.enable_split_screen(True)  # enable split screen
                return
        if not self.auto_opened:
            self.auto_opened = True
            self.open(load=load)

    def close(self):
        """Close HTML canvas dialog"""
        self.opened = False
        self.signals.closed.emit()
        self.window.ui.dialogs.close(self.dialog_id)
        self.update()

    def toggle(self):
        """Toggle HTML canvas dialog open/close"""
        if self.opened:
            self.close()
        else:
            self.open()

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = 'txt'):
        """
        Handle save as signal

        :param text: Data to save
        :param type: File type
        """
        if type == 'html':
            text = output_clean_html(text)
        else:
            text = output_html2text(text)
        # fix: QTimer required here to prevent crash if signal emitted from WebEngine window
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text, type))

    def show_hide(self, show: bool = True):
        """
        Show/hide HTML canvas window

        :param show: show/hide
        """
        if show:
            self.open()
        else:
            self.close()

    def get_toolbar_icon(self) -> QWidget:
        """
        Get toolbar icon

        :return: QWidget
        """
        return self.window.ui.nodes['icon.web_browser']

    def toggle_icon(self, state: bool):
        """
        Toggle canvas icon

        :param state: State
        """
        self.get_toolbar_icon().setVisible(state)

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["web_browser"] = QAction(
            QIcon(":/icons/web_on.svg"),
            trans("menu.tools.web_browser"),
            self.window,
            checkable=False,
        )
        actions["web_browser"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def as_tab(self, tab: Tab) -> QWidget:
        """
        Spawn and return tab instance

        :param tab: Parent Tab instance
        :return: Tab widget instance
        """

        tool = Tool(window=self.window, tool=self)  # dialog
        tool_widget = tool.as_tab()  # ToolWidget
        widget = TabWidget()
        widget.from_tool(tool_widget)
        widget.setup()
        tool.set_tab(tab)
        return widget

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = Tool(window=self.window, tool=self)
        self.dialog.setup()

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.web_browser': 'menu.tools.web_browser',
            }
        }