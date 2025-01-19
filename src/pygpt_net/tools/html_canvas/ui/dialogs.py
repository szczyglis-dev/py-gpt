#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QVBoxLayout

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

from .widgets import ToolWidget

class Tool:
    def __init__(self, window=None, tool=None):
        """
        HTML/JS canvas dialog

        :param window: Window instance
        :param tool: Tool instance
        """
        self.window = window
        self.tool = tool  # tool instance
        self.widget = ToolWidget(window, tool)
        self.layout = None
        self.menu_bar = None
        self.menu = {}
        self.actions = {}  # menu actions

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.menu["file"] = self.menu_bar.addMenu(trans("menu.file"))

        self.actions["file.open"] = QAction(QIcon(":/icons/folder.svg"), trans("tool.html_canvas.menu.file.open"))
        self.actions["file.open"].triggered.connect(
            lambda: self.tool.open_file()
        )
        self.actions["file.save_as"] = QAction(QIcon(":/icons/save.svg"), trans("tool.html_canvas.menu.file.save_as"))
        self.actions["file.save_as"].triggered.connect(
            lambda: self.widget.output.signals.save_as.emit(
                re.sub(r'\n{2,}', '\n\n', self.widget.output.html_content), 'html')
        )
        self.actions["file.reload"] = QAction(QIcon(":/icons/reload.svg"), trans("tool.html_canvas.menu.file.reload"))
        self.actions["file.reload"].triggered.connect(
            lambda: self.tool.reload_output()
        )
        self.actions["file.clear"] = QAction(QIcon(":/icons/close.svg"), trans("tool.html_canvas.menu.file.clear"))
        self.actions["file.clear"].triggered.connect(
            lambda: self.tool.clear()
        )

        # add actions
        self.menu["file"].addAction(self.actions["file.open"])
        self.menu["file"].addAction(self.actions["file.save_as"])
        self.menu["file"].addAction(self.actions["file.reload"])
        self.menu["file"].addAction(self.actions["file.clear"])
        return self.menu_bar

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.widget.set_tab(tab)

    def setup(self):
        """Setup canvas dialog"""
        self.layout = self.widget.setup()
        self.layout.setMenuBar(self.setup_menu())  # add menu bar

        id = self.tool.get_dialog_id()
        dialog = ToolDialog(window=self.window, tool=self.tool)
        dialog.setLayout(self.layout)
        dialog.setWindowTitle(trans("dialog.html_canvas.title"))
        dialog.resize(800, 500)
        self.window.ui.dialog[id] = dialog

    def get_widget(self) -> ToolWidget:
        """
        Get widget

        :return: ToolWidget
        """
        return self.widget

    def get_tab(self) -> QVBoxLayout:
        """
        Get layout

        :return: QVBoxLayout
        """
        return self.layout


class ToolDialog(BaseDialog):
    def __init__(self, window=None, id="html_canvas", tool=None):
        """
        HTML canvas dialog

        :param window: main window
        :param id: logger id
        """
        super(ToolDialog, self).__init__(window, id)
        self.window = window
        self.tool = tool

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(ToolDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(ToolDialog, self).keyPressEvent(event)

    def cleanup(self):
        """Cleanup on close"""
        if self.window is None or self.tool is None:
            return
        self.tool.opened = False
        self.tool.close()
        self.tool.update()
