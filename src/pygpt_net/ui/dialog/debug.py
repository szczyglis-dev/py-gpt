#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QScrollArea, QSplitter, QPlainTextEdit

from pygpt_net.ui.widget.dialog.debug import DebugDialog
from pygpt_net.ui.widget.lists.debug import DebugList
from pygpt_net.ui.widget.textarea.editor import CodeEditor


class Debug:
    def __init__(self, window=None):
        """
        Debug setup

        :param window: Window instance
        """
        self.window = window

    def setup(self, id: str):
        """
        Setup debug dialog

        :param id: debug id
        """
        self.window.ui.debug[id] = DebugList(self.window)

        scroll = QScrollArea()
        scroll.setWidget(self.window.ui.debug[id])
        scroll.setWidgetResizable(True)

        # data viewer
        viewer = CodeEditor(self.window)
        viewer.setReadOnly(True)
        self.window.ui.debug[id].viewer = viewer

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(viewer)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout = QGridLayout()
        layout.addWidget(splitter, 1, 0)

        self.window.ui.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.ui.dialog['debug.' + id].setLayout(layout)
        self.window.ui.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)
