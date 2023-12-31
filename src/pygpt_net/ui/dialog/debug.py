#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QGridLayout, QScrollArea

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

        layout = QGridLayout()
        layout.addWidget(scroll, 1, 0)

        self.window.ui.dialog['debug.' + id] = DebugDialog(self.window, id)
        self.window.ui.dialog['debug.' + id].setLayout(layout)
        self.window.ui.dialog['debug.' + id].setWindowTitle("Debug" + ": " + id)
