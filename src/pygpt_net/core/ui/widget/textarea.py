#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QTextEdit, QApplication, QTextBrowser


class NameInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        AI or user name input

        :param window: main window
        :param id: input id
        """
        super(NameInput, self).__init__(window)
        self.window = window
        self.id = id
        self.setStyleSheet(self.window.controller.theme.get_style('line_edit'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(NameInput, self).keyPressEvent(event)
        self.window.controller.ui.update_tokens()
        self.window.controller.presets.update_field(self.id, self.text(), self.window.config.get('preset'), True)


class ChatInput(QTextEdit):
    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super(ChatInput, self).__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.setFocus()
        self.value = self.window.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(ChatInput, self).keyPressEvent(event)
        self.window.controller.ui.update_tokens()
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            mode = self.window.config.get('send_mode')
            if mode > 0:
                if mode == 2:
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier:
                        self.window.controller.input.user_send()
                else:
                    self.window.controller.input.user_send()
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

            self.window.config.data['font_size.input'] = self.value
            self.window.config.save()
            self.window.controller.settings.update_font_size()
            event.accept()
        else:
            super(ChatInput, self).wheelEvent(event)


class ChatOutput(QTextBrowser):
    def __init__(self, window=None):
        """
        Chat output

        :param window: main window
        """
        super(ChatOutput, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.value = self.window.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8

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

            self.window.config.data['font_size'] = self.value
            self.window.config.save()
            self.window.controller.settings.update_font_size()
            event.accept()
        else:
            super(ChatOutput, self).wheelEvent(event)


class NotepadOutput(QTextEdit):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.value = self.window.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(NotepadOutput, self).keyPressEvent(event)
        self.window.controller.notepad.save()

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

            self.window.config.data['font_size'] = self.value
            self.window.config.save()
            self.window.controller.settings.update_font_size()
            event.accept()
        else:
            super(NotepadOutput, self).wheelEvent(event)


class RenameInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Rename dialog

        :param window: main window
        :param id: info window id
        """
        super(RenameInput, self).__init__(window)

        self.window = window
        self.id = id
        self.setStyleSheet(self.window.controller.theme.get_style('line_edit'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(RenameInput, self).keyPressEvent(event)
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.confirm.accept_rename(self.window.dialog['rename'].id,
                                                         self.window.dialog['rename'].current,
                                                         self.text())
