#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 00:00:00                  #
# ================================================== #

import os
from typing import Dict

from PySide6.QtCore import QTimer, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog, QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans

from .ui.dialogs import Tool
from .ui.widgets import ToolWidget, ToolSignals


class HtmlCanvas(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        HTML/JS Canvas

        :param window: Window instance
        """
        super(HtmlCanvas, self).__init__(*args, **kwargs)
        self.id = "html_canvas"
        self.dialog_id = "html_canvas"
        self.has_tab = True
        self.tab_title = "menu.tools.html_canvas"
        self.tab_icon = ":/icons/code.svg"
        self.opened = False
        self.is_edit = False
        self.auto_clear = True
        self.dialog = None
        self.is_edit = False
        self.auto_opened = False
        self.file_output = ".canvas.html"
        self.signals = ToolSignals()

    def setup(self):
        """Setup"""
        self.load_output()
        self.update()

    def on_reload(self):
        """On app profile reload"""
        self.setup()

    def update(self):
        """Update menu"""
        self.update_menu()

    def toggle_edit(self, widget: ToolWidget):
        """
        Toggle edit mode

        :param widget: Canvas widget
        """
        current = self.is_edit
        self.is_edit = not self.is_edit
        widget.edit.setVisible(self.is_edit)
        widget.output.setVisible(not self.is_edit)
        if current:
            self.set_output(widget.edit.toPlainText())
            self.save_output()

    def update_menu(self):
        """Update menu"""
        """
        if self.opened:
            self.window.ui.menu['tools.html_canvas'].setChecked(True)
        else:
            self.window.ui.menu['tools.html_canvas'].setChecked(False)
        """

    def get_current_path(self) -> str:
        """
        Get current output path

        :return: Output path
        """
        return os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)

    def get_dialog_id(self) -> str:
        """
        Get dialog ID

        :return: Dialog ID
        """
        return self.dialog_id

    def set_output(self, output: str):
        """
        Set output HTML

        :param output: Output HTML code
        """
        path = self.get_current_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(output)
        if os.path.exists(path):
            self.signals.reload.emit(path)
        self.signals.update.emit(output)

    def reload_output(self):
        """Reload output data"""
        self.load_output()
        self.update()

    def get_output(self) -> str:
        """
        Get current HTML output

        :return: Output data
        """
        path = self.get_current_path()
        data = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        return data

    def load_output(self):
        """Load output data from file"""
        path = self.get_current_path()
        data = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        self.set_output(data)

    def save_output(self):
        """Save output data to file"""
        path = self.get_current_path()
        data = self.get_output()
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def clear_output(self):
        """Clear output"""
        path = self.get_current_path()
        if os.path.exists(path):
            os.remove(path)
        self.set_output("")

    def clear(self, force: bool = False):
        """
        Clear current window

        :param force: Force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='html_canvas.clear',
                id=0,
                msg=trans("html_canvas.clear.confirm"),
            )
            return
        self.clear_output()

    def clear_all(self):
        """Clear input and output"""
        self.clear_output()

    def open(self):
        """Open HTML canvas dialog"""
        if not self.opened:
            self.opened = True
            self.auto_opened = False
            self.load_output()
            self.window.ui.dialogs.open(self.dialog_id, width=800, height=600)
            self.update()

    def auto_open(self):
        """Auto open canvas dialog"""
        if self.window.controller.ui.tabs.is_current_tool(self.id):
            tool_col = self.window.controller.ui.tabs.get_tool_column(self.id)
            current_col = self.window.controller.ui.tabs.column_idx
            if tool_col == 1 and tool_col != current_col:
                self.window.ui.splitters['columns'].setSizes([1, 1])
                return
            return # do not open if already opened in tab
        if not self.auto_opened:
            self.auto_opened = True
            self.open()

    def open_file(self):
        """Open file dialog"""
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("HTML files (*.html)")
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
                self.set_output(data)
            self.open()

    def close(self):
        """Close HTML canvas dialog"""
        self.opened = False
        self.window.ui.dialogs.close(self.dialog_id)
        self.update()

    def toggle(self):
        """Toggle HTML canvas dialog open/close"""
        if self.opened:
            self.close()
        else:
            self.open()

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
        return self.window.ui.nodes['icon.html_canvas']

    def toggle_icon(self, state: bool):
        """
        Toggle canvas icon

        :param state: State
        """
        self.get_toolbar_icon().setVisible(state)

    def get_current_output(self) -> str:
        """
        Get current output from canvas

        :return: Output data
        """
        return self.get_output()

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

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["html_canvas"] = QAction(
            QIcon(":/icons/code.svg"),
            trans("menu.tools.html_canvas"),
            self.window,
            checkable=False,
        )
        actions["html_canvas"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def as_tab(self, tab: Tab) -> QWidget:
        """
        Spawn and return tab instance

        :param tab: Parent Tab instance
        :return: Tab widget instance
        """
        canvas = Tool(window=self.window, tool=self)
        layout = canvas.widget.setup()
        widget = QWidget()
        widget.setLayout(layout)
        canvas.set_tab(tab)
        self.load_output()
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
                'tools.html_canvas': 'menu.tools.html_canvas',
            }
        }