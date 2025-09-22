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

    def as_tab(self) -> ToolWidget:
        """
        Return tool as tab

        :return: ToolWidget
        """
        return self.widget

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.widget.set_tab(tab)

    def setup(self):
        """Setup canvas dialog"""
        self.layout = self.widget.setup()

        id = self.tool.get_dialog_id()
        dialog = ToolDialog(window=self.window, tool=self.tool)
        dialog.setLayout(self.layout)
        dialog.setWindowTitle(trans("menu.tools.web_browser"))
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
