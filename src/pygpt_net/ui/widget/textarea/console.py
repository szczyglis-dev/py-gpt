#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 18:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit

class ConsoleInput(QLineEdit):
    def __init__(self, window=None):
        """
        Console input

        :param window: main window
        """
        super(ConsoleInput, self).__init__(window)
        self.window = window
        self.setPlaceholderText("Console... Type your command here")
        self.setProperty('class', 'text-editor')
        self.setFocus()

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        handled = False
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.window.core.debug.console.on_send()
            handled = True
            self.setFocus()
        if not handled:
            super(ConsoleInput, self).keyPressEvent(event)
