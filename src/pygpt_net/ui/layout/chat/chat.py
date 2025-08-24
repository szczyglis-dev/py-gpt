#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, Slot
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
        input_widget = self.input.setup()
        output_widget = self.output.setup()

        splitter = QSplitter(Qt.Vertical)
        self.window.ui.splitters['main.output'] = splitter
        splitter.addWidget(output_widget)
        splitter.addWidget(input_widget)
        splitter.setStretchFactor(0, 9)  # Output widget stretch factor
        splitter.setStretchFactor(1, 1)  # Input widget stretch factor
        splitter.splitterMoved.connect(self.on_splitter_moved)
        self.window.controller.ui.splitter_output_size_input = splitter.sizes()

        return splitter

    @Slot(int, int)
    def on_splitter_moved(self, pos, index):
        """
        Store the size of the output splitter when it is moved
        """
        tabs = self.window.ui.tabs
        if "input" not in tabs:
            return
        splitter = self.window.ui.splitters.get('main.output')
        if splitter is None:
            return
        idx = tabs['input'].currentIndex()
        sizes = splitter.sizes()
        if idx != 0:
            self.window.controller.ui.splitter_output_size_files = sizes
        else:
            self.window.controller.ui.splitter_output_size_input = sizes