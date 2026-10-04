#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget
from pygpt_net.ui.widget.tabs.layout import OutputLayout


class Output:
    def __init__(self, window=None):
        """
        Chat output UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup output

        :return: QWidget
        """
        self.window.ui.layout = OutputLayout(self.window)
        self.window.ui.nodes['output'] = {}
        self.window.ui.nodes['output_plain'] = {}

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.layout)
        layout.setContentsMargins(0, 5, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        return widget
