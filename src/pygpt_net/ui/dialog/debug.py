#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QScrollArea, QSplitter, QPlainTextEdit

from pygpt_net.ui.widget.dialog.debug import DebugDialog
from pygpt_net.ui.widget.lists.debug import DebugList


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
        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        self.window.ui.debug[id].viewer = viewer

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(viewer)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout = QGridLayout()
        layout.addWidget(splitter, 1, 0)

        self.window.ui.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.ui.dialog['debug.' + id].setLayout(layout)
        self.window.ui.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)
