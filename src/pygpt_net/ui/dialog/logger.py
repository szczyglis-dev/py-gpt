#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.20 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout

from pygpt_net.ui.widget.dialog.logger import LoggerDialog
from pygpt_net.ui.widget.textarea.console import ConsoleInput
from pygpt_net.ui.widget.textarea.editor import CodeEditor
from pygpt_net.utils import trans


class Logger:
    def __init__(self, window=None):
        """
        Logger dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup logger dialog"""
        self.window.logger = CodeEditor(self.window)
        self.window.logger.setReadOnly(True)
        self.window.logger.setProperty('class', 'text-editor')

        self.window.console = ConsoleInput(self.window)

        # TAB completion commands
        if hasattr(self.window.core.debug, "console") and hasattr(self.window.core.debug.console, "get_supported_commands"):
            self.window.console.set_commands(self.window.core.debug.console.get_supported_commands())

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.window.core.debug.console.on_send)

        console_layout = QHBoxLayout()
        console_layout.addWidget(self.window.console)
        console_layout.addWidget(send_btn)
        console_layout.setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['logger.btn.clear'] = QPushButton(trans("dialog.logger.btn.clear"))
        self.window.ui.nodes['logger.btn.clear'].clicked.connect(
            lambda: self.window.controller.debug.clear_logger()
        )

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['logger.btn.clear'])

        layout = QVBoxLayout()
        layout.addWidget(self.window.logger)
        layout.addLayout(console_layout)
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['logger'] = LoggerDialog(self.window)
        self.window.ui.dialog['logger'].setLayout(layout)
        self.window.ui.dialog['logger'].setWindowTitle(trans('dialog.logger.title'))
        self.window.ui.dialog['logger'].resize(800, 500)