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
        self.window.controller.ui.update()
        self.window.controller.presets.update_field(self.id, self.text(), self.window.config.get('preset'), True)


class ChatInput(QTextEdit):
    def __init__(self, window=None):
        """
        Chat input

        :param window: main window
        """
        super(ChatInput, self).__init__(window)
        self.window = window
        self.setFocus()

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(ChatInput, self).keyPressEvent(event)
        self.window.controller.ui.update()
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


class NotepadOutput(QTextEdit):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.setStyleSheet(self.window.controller.theme.get_style('chat_output'))

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(NotepadOutput, self).keyPressEvent(event)
        self.window.controller.notepad.save()


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
