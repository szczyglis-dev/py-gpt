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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from pygpt_net.ui.layout.chat.input import Input
from pygpt_net.ui.layout.chat.output import Output


class ChatMain:
    def __init__(self, window=None):
        """
        Chat UI

        :param window: Window instance
        """
        self.window = window
        self.input = Input(window)
        self.output = Output(window)

    def setup(self):
        """
        Setup chat main layout

        :return: QSplitter
        :rtype: QSplitter
        """
        input = self.input.setup()
        output = self.output.setup()

        # main vertical splitter
        self.window.ui.splitters['main.output'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['main.output'].addWidget(output)
        self.window.ui.splitters['main.output'].addWidget(input)
        self.window.ui.splitters['main.output'].setStretchFactor(0, 4)
        self.window.ui.splitters['main.output'].setStretchFactor(1, 1)

        return self.window.ui.splitters['main.output']
