#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget
from datetime import datetime, timedelta

from pygpt_net.ui.widget.lists.context import ContextList
from pygpt_net.ui.widget.textarea.search_input import CtxSearchInput
from pygpt_net.utils import trans


class SearchInput:
    def __init__(self, window=None):
        """
        Context search input

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup search input

        :return: QWidget
        """
        self.window.ui.nodes['ctx.search'] = CtxSearchInput(self.window)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['ctx.search'])
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setContentsMargins(0, 0, 0, 0)

        return widget
