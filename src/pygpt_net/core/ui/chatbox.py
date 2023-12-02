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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSplitter

from ..ui.widgets import ChatOutput
from ..ui.input import Input
from ..utils import trans


class ChatBox:
    def __init__(self, window=None):
        """
        Chatbox UI

        :param window: main window object
        """
        self.window = window
        self.input = Input(window)

    def setup(self):
        """
        Setups chatbox

        :return: QSplitter
        """
        self.window.layout_input = self.input.setup()

        self.window.data['output'] = ChatOutput(self.window)
        self.window.data['chat.model'] = QLabel("")
        self.window.data['chat.model'].setAlignment(Qt.AlignRight)
        context_layout = self.setup_context()

        self.window.data['chat.label'] = QLabel(trans("chatbox.label"))
        self.window.data['chat.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        self.window.data['chat.plugins'] = QLabel("")
        self.window.data['chat.plugins'].setAlignment(Qt.AlignCenter)

        header = QHBoxLayout()
        header.addWidget(self.window.data['chat.label'])
        header.addWidget(self.window.data['chat.plugins'])
        header.addWidget(self.window.data['chat.model'])

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.data['output'])
        layout.addLayout(context_layout)

        output_widget = QWidget()
        output_widget.setLayout(layout)

        input_widget = QWidget()
        input_widget.setLayout(self.window.layout_input)

        # main vertical splitter
        vsplitter = QSplitter(Qt.Vertical)
        vsplitter.addWidget(output_widget)
        vsplitter.addWidget(input_widget)
        vsplitter.setStretchFactor(0, 4)
        vsplitter.setStretchFactor(1, 1)

        return vsplitter

    def setup_context(self):
        """
        Setups context

        :return: QHBoxLayout        
        """
        self.window.data['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        self.window.data['output.timestamp'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows style fix
        self.window.data['output.timestamp'].stateChanged.connect(
            lambda: self.window.controller.output.toggle_timestamp(self.window.data['output.timestamp'].isChecked()))

        self.window.data['prompt.context'] = QLabel("")
        self.window.data['prompt.context'].setAlignment(Qt.AlignRight)

        layout = QHBoxLayout()
        layout.addWidget(self.window.data['output.timestamp'])
        layout.addWidget(self.window.data['prompt.context'])

        return layout
