#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar

from pygpt_net.utils import trans
from .base import BaseDialog

import pygpt_net.icons_rc

class EditorFileDialog(BaseDialog):
    def __init__(self, window=None, id="editor_file"):
        """
        File editor dialog

        :param window: main window
        :param id: dialog id
        """
        super(EditorFileDialog, self).__init__(window, id)
        self.window = window
        self.file = None
        self.base_content = None
        self.disable_geometry_store = False
        self.id = id

    def update_file_title(self, force: bool = False):
        """
        Update file edited time title

        :param force: force update
        """
        if self.file:
            current = self.window.ui.editor[self.id].toPlainText()
            base = self.base_content
            title = os.path.basename(self.file)
            if current != base:
                title += "*"
            if current != base or force:
                time = datetime.datetime.now().strftime("%H:%M")
                title += " (" + time + ")"
            self.setWindowTitle(title)
        else:
            self.setWindowTitle("Untitled")

    def setup_menu(self) -> QMenuBar:
        """Setup menu"""
        self.menu_bar = QMenuBar()
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        self.actions = {}

        # open
        self.actions["open"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open"))
        self.actions["open"].triggered.connect(
            lambda: self.window.tools.editor.open_file(self.id, auto_close=True)
        )

        # open (new window)
        self.actions["open_new"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open_new_window"))
        self.actions["open_new"].triggered.connect(
            lambda: self.window.tools.editor.open_file(self.id, auto_close=False)
        )

        # save
        self.actions["save"] = QAction(QIcon(":/icons/save"), trans("action.save"))
        self.actions["save"].triggered.connect(
            lambda: self.window.tools.editor.save(self.id)
        )

        # save as
        self.actions["save_as"] = QAction(QIcon(":/icons/save"), trans("action.save_as"))
        self.actions["save_as"].triggered.connect(
            lambda: self.window.tools.editor.save_as_file(self.id)
        )

        # close
        self.actions["exit"] = QAction(QIcon(":/icons/logout.svg"), trans("menu.file.exit"))
        self.actions["exit"].triggered.connect(
            lambda: self.window.tools.editor.close(self.id)
        )

        # add actions
        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["open_new"])
        self.file_menu.addAction(self.actions["save"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])

        return self.menu_bar

    def append_layout(self, layout):
        """
        Update layout

        :param layout: layout
        """
        layout.setMenuBar(self.setup_menu())  # attach menu
        self.setLayout(layout)

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(EditorFileDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(EditorFileDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        if self.id == "editor_file":
            self.window.core.settings.active['editor'] = False
            self.window.controller.settings.close('editor')
            self.window.controller.settings.update()
