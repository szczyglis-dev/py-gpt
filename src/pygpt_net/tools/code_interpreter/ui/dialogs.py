#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.code_interpreter.ui.widgets import ToolWidget
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

class Tool:
    def __init__(self, window=None, tool=None):
        """
        Python interpreter dialog

        :param window: Window instance
        :param tool: Tool instance
        """
        self.window = window
        self.tool = tool  # tool instance
        self.layout = None
        self.widget = ToolWidget(window, tool)
        self.menu_bar = None
        self.menu = {}
        self.actions = {}  # menu actions
        self.is_dialog = False

    def as_tab(self) -> ToolWidget:
        """
        Return tool as tab

        :return: ToolWidget
        """
        self.set_is_dialog(False)
        return self.widget

    def set_is_dialog(self, is_dialog: bool):
        """
        Set if dialog

        :param is_dialog: bool
        """
        self.is_dialog = is_dialog
        if self.widget:
            self.widget.set_is_dialog(is_dialog)
        else:
            print("Warning: Tool widget is not initialized, cannot set is_dialog.")

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        if self.widget:
            self.widget.set_tab(tab)
        else:
            print("Warning: Tool widget is not initialized, cannot set tab.")

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.menu_bar.setNativeMenuBar(False)
        self.menu["file"] = self.menu_bar.addMenu(trans("interpreter.menu.file"))
        self.menu["kernel"] = self.menu_bar.addMenu(trans("interpreter.menu.kernel"))

        self.actions["file.clear_output"] = QAction(QIcon(":/icons/close.svg"),
                                                    trans("interpreter.menu.file.clear_output"))
        self.actions["file.clear_output"].triggered.connect(
            lambda: self.tool.clear_output()
        )
        self.actions["file.clear_history"] = QAction(QIcon(":/icons/close.svg"),
                                                    trans("interpreter.menu.file.clear_history"))
        self.actions["file.clear_history"].triggered.connect(
            lambda: self.tool.clear_history()
        )
        self.actions["file.clear_all"] = QAction(QIcon(":/icons/close.svg"),
                                                   trans("interpreter.menu.file.clear_all"))
        self.actions["file.clear_all"].triggered.connect(
            lambda: self.tool.clear_all()
        )

        self.actions["kernel.restart"] = QAction(QIcon(":/icons/reload.svg"),
                                                      trans("interpreter.menu.kernel.restart"))
        self.actions["kernel.restart"].triggered.connect(
            lambda: self.tool.restart_kernel()
        )

        # add actions
        self.menu["file"].addAction(self.actions["file.clear_output"])
        self.menu["file"].addAction(self.actions["file.clear_history"])
        self.menu["file"].addAction(self.actions["file.clear_all"])
        self.menu["kernel"].addAction(self.actions["kernel.restart"])
        return self.menu_bar

    def setup(self):
        """Setup interpreter dialog"""
        self.layout = self.widget.setup(all=True)
        self.layout.setMenuBar(self.setup_menu())  # add menu bar

        self.window.ui.dialog['interpreter'] = ToolDialog(self.window)
        self.window.ui.dialog['interpreter'].setLayout(self.layout)
        self.window.ui.dialog['interpreter'].setWindowTitle(trans("dialog.interpreter.title"))
        self.window.ui.dialog['interpreter'].resize(800, 500)


class ToolDialog(BaseDialog):
    def __init__(self, window=None, id="interpreter"):
        """
        Interpreter dialog

        :param window: main window
        :param id: logger id
        """
        super(ToolDialog, self).__init__(window, id)
        self.window = window

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
        """
        Cleanup on close
        """
        if self.window is None:
            return
        self.window.tools.get("interpreter").opened = False
        self.window.tools.get("interpreter").close()
        self.window.tools.get("interpreter").update()
