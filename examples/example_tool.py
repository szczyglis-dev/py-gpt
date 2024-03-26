#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 15:00:00                  #
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
        self.id = "example_tool"
        self.dialog = None
        self.opened = False

    def setup(self):
        """Setup"""
        pass

    def update(self):
        """Update"""
        pass

    def open(self):
        """Open dialog"""
        print("Opening...")
        self.window.ui.dialogs.open('example.tool', width=800, height=600)
        self.opened = True
        self.update()

    def close(self):
        """Close dialog"""
        print("Closing...")
        self.window.ui.dialogs.close('example.tool')
        self.opened = False

    def toggle(self):
        """Toggle dialog"""
        print("On toggle...")
        if self.opened:
            self.close()
        else:
            self.open()

    def hello_world(self):
        """Example action"""
        print("Hello World!")
        self.window.ui.dialogs.alert("Hello World!")

    def show_hide(self, show: bool = True):
        """
        Show/hide window

        :param show: show/hide
        """
        print("On show/hide...")
        if show:
            self.open()
        else:
            self.close()

    def on_close(self):
        """On close"""
        self.opened = False
        print("On close...")

    def on_exit(self):
        """On exit"""
        print("On app exit...")

    def setup_menu(self) -> dict:
        """
        Setup main menu

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
        self.dialog = ExampleDialogWidget(self.window)
        self.dialog.setup()

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.example.tool': 'menu.tools.example.tool',
            }
        }

class ExampleDialogWidget:
    def __init__(self, window=None):
        """
        Example Dialog

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}

    def setup_menu(self) -> QMenuBar:
        """Setup dialog menu"""
        self.menu_bar = QMenuBar()
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))

        # example action
        self.actions["example"] = QAction(QIcon(":/icons/folder.svg"), "Example")
        self.actions["example"].triggered.connect(
            lambda: self.window.tools.get("example_tool").hello_world()
        )

        # add actions
        self.file_menu.addAction(self.actions["example"])
        return self.menu_bar

    def setup(self):
        """Setup dialog"""
        label = QLabel("Hello World!")
        btn = QPushButton("Example action!")
        btn.clicked.connect(
            lambda: self.window.tools.get("example_tool").hello_world()
        )

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())
        layout.addWidget(label, alignment=Qt.AlignCenter)
        layout.addWidget(btn)

        self.window.ui.dialog['example.tool'] = ExampleDialog(self.window)
        self.window.ui.dialog['example.tool'].setLayout(layout)
        self.window.ui.dialog['example.tool'].setWindowTitle("Example Dialog")


class ExampleDialog(BaseDialog):
    def __init__(self, window=None):
        """
        Dialog

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
        """
        Cleanup on close
        """
        self.window.tools.get("example_tool").on_close()