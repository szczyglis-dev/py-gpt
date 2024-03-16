#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QSplitter

from pygpt_net.ui.widget.dialog.interpreter import InterpreterDialog
from pygpt_net.ui.widget.textarea.python_input import PythonInput
from pygpt_net.ui.widget.textarea.python_output import PythonOutput
from pygpt_net.utils import trans


class Interpreter:
    def __init__(self, window=None):
        """
        Interpreter dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup interpreter dialog"""
        self.window.interpreter = PythonOutput(self.window)
        self.window.interpreter.setReadOnly(True)

        self.window.ui.nodes['interpreter.btn.clear'] = QPushButton(trans("dialog.logger.btn.clear"))
        self.window.ui.nodes['interpreter.btn.clear'].clicked.connect(
            lambda: self.window.controller.interpreter.clear())
        self.window.ui.nodes['interpreter.btn.send'] = QPushButton("Send and execute")
        self.window.ui.nodes['interpreter.btn.send'].clicked.connect(
            lambda: self.window.controller.interpreter.send_input())

        self.window.ui.nodes['interpreter.input'] = PythonInput(self.window)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.btn.clear'])
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.btn.send'])

        self.window.ui.splitters['interpreter'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['interpreter'].addWidget(self.window.interpreter)
        self.window.ui.splitters['interpreter'].addWidget(self.window.ui.nodes['interpreter.input'])
        self.window.ui.splitters['interpreter'].setStretchFactor(0, 4)
        self.window.ui.splitters['interpreter'].setStretchFactor(1, 1)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['interpreter'])
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['interpreter'] = InterpreterDialog(self.window)
        self.window.ui.dialog['interpreter'].setLayout(layout)
        self.window.ui.dialog['interpreter'].setWindowTitle("Python code interpreter")
        self.window.ui.dialog['interpreter'].resize(800, 500)
