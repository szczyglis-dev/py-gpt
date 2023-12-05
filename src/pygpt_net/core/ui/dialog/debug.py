#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTreeView, QGridLayout, QAbstractItemView, QScrollArea

from ..widgets import DebugDialog


class Debug:
    def __init__(self, window=None):
        """
        Debug setup

        :param window: main UI window object
        """
        self.window = window

    def setup(self, id):
        """
        Setups debug dialog

        :param id: debug id
        """
        self.window.debug[id] = QTreeView()
        self.window.debug[id].setRootIsDecorated(False)
        self.window.debug[id].setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.window.debug[id].setWordWrap(True)

        scroll = QScrollArea()
        scroll.setWidget(self.window.debug[id])
        scroll.setWidgetResizable(True)

        layout = QGridLayout()
        layout.addWidget(scroll, 1, 0)

        self.window.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.dialog['debug.' + id].setLayout(layout)
        self.window.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)
