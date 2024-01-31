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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


class Status:
    def __init__(self, window=None):
        """
        Input UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QHBoxLayout:
        """
        Setup status bar

        :return: QHBoxLayout
        """
        self.window.ui.nodes['status'] = QLabel(trans('status.started'))
        self.window.ui.nodes['status.agent'] = HelpLabel("")
        self.window.ui.nodes['status.agent'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes['status.agent'])
        layout.addWidget(self.window.ui.nodes['status'])
        layout.setAlignment(Qt.AlignLeft)

        return layout
