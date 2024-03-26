#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 15:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit, QApplication

from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor

import pygpt_net.icons_rc


class PythonInput(QTextEdit):
    def __init__(self, window=None):
        """
        Python interpreter input

        :param window: main window
        """
        super(PythonInput, self).__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-input')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.textChanged.connect(
            lambda: self.window.tools.get("interpreter").update_input()
        )
        self.setFocus()

    def update_stylesheet(self, data: str):
        """
        Update stylesheet

        :param data: stylesheet CSS
        """
        self.setStyleSheet(self.default_stylesheet + data)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(PythonInput, self).keyPressEvent(event)
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:  # Enter or Shift + Enter
                if mode == 2:  # Shift + Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier:
                        self.window.tools.get("interpreter").send_input()
                else:  # Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers != QtCore.Qt.ShiftModifier:
                        self.window.tools.get("interpreter").send_input()
                self.setFocus()

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            size_str = f"{self.value}px"
            self.update_stylesheet(f"font-size: {size_str};")
            event.accept()
        else:
            super(PythonInput, self).wheelEvent(event)


class PythonOutput(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(PythonOutput, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-output')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
