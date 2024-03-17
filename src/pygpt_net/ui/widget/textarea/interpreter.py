#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.17 09:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit, QApplication, QPlainTextEdit
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
        self.value = self.window.core.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8
        self.setFocus()

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

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
                        self.window.controller.interpreter.send_input()
                else:  # Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers != QtCore.Qt.ShiftModifier:
                        self.window.controller.interpreter.send_input()
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

            self.window.core.config.data['font_size.input'] = self.value
            self.window.core.config.save()
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(PythonInput, self).wheelEvent(event)


class PythonOutput(QPlainTextEdit):
    def __init__(self, window=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(PythonOutput, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.textChanged.connect(self.window.controller.interpreter.save_edit)

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

            self.window.core.config.data['font_size'] = self.value
            self.window.core.config.save()
            option = self.window.controller.settings.editor.get_option('font_size')
            option['value'] = self.value
            self.window.controller.config.apply(
                parent_id='config',
                key='font_size',
                option=option,
            )
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(PythonOutput, self).wheelEvent(event)
