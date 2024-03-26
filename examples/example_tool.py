#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout, QMenuBar

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans


class ExampleTool(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        ExampleTool

        :param window: Window instance
        """
        super(ExampleTool, self).__init__(*args, **kwargs)
        self.id = "example_tool"  # unique tool id
        self.dialog = None
        self.opened = False

    def setup(self):
        """Setup tool"""
        # setup actions here
        print("Setting up example tool...")

    def update(self):
        """Update"""
        # update actions here (e.g. menu update, etc.)
        print("On update example tool...")

    def open(self):
        """Open dialog window"""
        print("Opening example dialog...")
        self.window.ui.dialogs.open('example_dialog', width=800, height=600)
        self.opened = True
        self.update()

    def close(self):
        """Close dialog window"""
        print("Closing example dialog...")
        self.window.ui.dialogs.close('example_dialog')
        self.opened = False

    def toggle(self):
        """Toggle dialog window"""
        print("On example dialog toggle...")
        if self.opened:
            self.close()
        else:
            self.open()

    def example_action(self):
        """Example action"""
        print("Hello World!")
        self.window.ui.dialogs.alert("Hello World!")  # show example alert

    def show_hide(self, show: bool = True):
        """
        Show/hide dialog window

        :param show: show/hide
        """
        print("On example dialog show/hide...")
        if show:
            self.open()
        else:
            self.close()

    def on_close(self):
        """On dialog close"""
        print("On example dialog close...")
        self.opened = False

    def on_exit(self):
        """On app exit"""
        print("On exiting example tool...")

    def setup_menu(self) -> dict:
        """
        Setup main menu (Tools)

        :return dict with menu actions
        """
        actions = {}
        actions["example.tool"] = QAction(
            QIcon(":/icons/warning.svg"),
            trans("example.tool"),
            self.window,
            checkable=False,
        )
        actions["example.tool"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        # build all static dialogs here
        self.dialog = DialogBuilder(self.window)
        self.dialog.setup()

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.example.tool': 'menu.tools.example.tool',  # menu key => translation key
            }
        }

class DialogBuilder:
    def __init__(self, window=None):
        """
        Example dialog builder

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}  # menu actions

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))

        # example action
        self.actions["example_action"] = QAction(QIcon(":/icons/folder.svg"), "Example menu action")
        self.actions["example_action"].triggered.connect(
            lambda: self.window.tools.get("example_tool").example_action()
        )

        # add actions
        self.file_menu.addAction(self.actions["example_action"])
        return self.menu_bar

    def setup(self):
        """Setup dialog window"""
        label = QLabel("Hello World!")
        btn = QPushButton("Example action!")
        btn.clicked.connect(
            lambda: self.window.tools.get("example_tool").example_action()
        )

        # layout
        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())  # add menu bar
        layout.addWidget(label, alignment=Qt.AlignCenter)
        layout.addWidget(btn)

        # add dialog to the window
        self.window.ui.dialog['example_dialog'] = ExampleDialog(self.window)
        self.window.ui.dialog['example_dialog'].setLayout(layout)
        self.window.ui.dialog['example_dialog'].setWindowTitle("Example Tool Dialog")


class ExampleDialog(BaseDialog):
    def __init__(self, window=None):
        """
        Example dialog

        :param window: main window
        """
        super(ExampleDialog, self).__init__(window)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(ExampleDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(ExampleDialog, self).keyPressEvent(event)

    def cleanup(self):
        """Cleanup on dialog close"""
        self.window.tools.get("example_tool").on_close()