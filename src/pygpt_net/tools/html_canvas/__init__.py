#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 23:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QTimer, Slot, QUrl
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog

from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.html_canvas.ui.dialogs import Canvas
from pygpt_net.utils import trans


class HtmlCanvas(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        HTML/JS canvas

        :param window: Window instance
        """
        super(HtmlCanvas, self).__init__(*args, **kwargs)
        self.id = "html_canvas"
        self.opened = False
        self.is_edit = False
        self.auto_clear = True
        self.dialog = None
        self.is_edit = False
        self.file_output = ".canvas.html"

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

    def toggle_edit(self):
        """Toggle edit mode"""
        current = self.is_edit
        self.is_edit = not self.is_edit
        self.window.ui.nodes['html_canvas.edit'].setVisible(self.is_edit)
        self.window.ui.nodes['html_canvas.output'].setVisible(not self.is_edit)
        if current:
            self.set_output(self.window.ui.nodes['html_canvas.edit'].toPlainText())
            self.save_output()
        self.window.ui.nodes['html_canvas.btn.edit'].setChecked(self.is_edit)

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

    def set_output(self, output: str):
        """
        Set output HTML

        :param output: Output HTML code
        """
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        with open(path, "w", encoding="utf-8") as f:
            f.write(output)
        if os.path.exists(path):
            self.window.ui.nodes['html_canvas.output'].setUrl(QUrl().fromLocalFile(path))
        self.window.ui.nodes['html_canvas.edit'].setPlainText(output)

    def reload_output(self):
        """Reload output data"""
        self.load_output()
        self.update()

    def get_output(self) -> str:
        """
        Get current HTML output

        :return: Output data
        """
        return self.window.ui.nodes['html_canvas.edit'].toPlainText()

    def load_output(self):
        """Load output data from file"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        data = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        self.set_output(data)

    def save_output(self):
        """Save output data to file"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        data = self.get_output()
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def clear_output(self):
        """Clear output"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
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
            self.load_output()
            self.window.ui.dialogs.open('html_canvas', width=800, height=600)
            self.update()

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
        self.window.ui.dialogs.close('html_canvas')
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

    def toggle_icon(self, state: bool):
        """
        Toggle canvas icon

        :param state: State
        """
        self.window.ui.nodes['icon.html_canvas'].setVisible(state)

    def get_current_output(self) -> str:
        """
        Get current output from canvas

        :return: Output data
        """
        return self.window.ui.nodes['html_canvas.output'].get_html_content()

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

    def setup_menu(self) -> dict:
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

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = Canvas(self.window)
        self.dialog.setup()

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.html_canvas': 'menu.tools.html_canvas',
            }
        }