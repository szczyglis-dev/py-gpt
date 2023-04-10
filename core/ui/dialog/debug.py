#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTreeView, QGridLayout

from core.ui.widgets import DebugDialog


class Debug:
    def __init__(self, window=None):
        """
        Debug setup

        :param window: main UI window object
        """
        self.window = window

    def setup(self, id):
        """
        Setup debug dialog

        :param id: debug id
        """
        self.window.debug[id] = QTreeView()
        self.window.debug[id].setRootIsDecorated(False)

        layout = QGridLayout()
        layout.addWidget(self.window.debug[id], 1, 0)

        self.window.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.dialog['debug.' + id].setLayout(layout)
        self.window.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)
