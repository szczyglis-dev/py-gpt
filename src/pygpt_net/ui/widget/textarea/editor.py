#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPlainTextEdit, QMenu

from pygpt_net.utils import trans

import pygpt_net.icons_rc


class BaseCodeEditor(QPlainTextEdit):
    def __init__(self, window=None):
        """
        Base code editor

        :param window: main window
        """
        super(BaseCodeEditor, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)

    def update_stylesheet(self, data: str):
        """
        Update stylesheet

        :param data: stylesheet CSS
        """
        self.setStyleSheet(self.default_stylesheet + data)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        selected_text = self.textCursor().selectedText()

        if selected_text:
            # plain text
            plain_text = self.textCursor().selection().toPlainText()

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            # copy to
            copy_to_menu = QMenu(trans('text.context_menu.copy_to'), self)

            # input
            action = QAction(QIcon(":/icons/input.svg"), trans('text.context_menu.copy_to.input'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.append_to_input(selected_text))
            copy_to_menu.addAction(action)

            # calendar
            action = QAction(QIcon(":/icons/schedule.svg"), trans('text.context_menu.copy_to.calendar'), self)
            action.triggered.connect(
                lambda: self.window.controller.calendar.note.append_text(selected_text))
            copy_to_menu.addAction(action)

            # notepad
            num_notepads = self.window.controller.notepad.get_num_notepads()
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    name = self.window.controller.notepad.get_notepad_name(i)
                    action = QAction(QIcon(":/icons/paste.svg"), name, self)
                    action.triggered.connect(lambda checked=False, i=i:
                                             self.window.controller.notepad.append_text(selected_text, i))
                    copy_to_menu.addAction(action)

            menu.addMenu(copy_to_menu)

            # save as (selected)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            # save as (all)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

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
            super(BaseCodeEditor, self).wheelEvent(event)


class CodeEditor(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Code editor

        :param window: main window
        """
        super(CodeEditor, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)

class TextFileEditor(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Code editor

        :param window: main window
        """
        super(TextFileEditor, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        selected_text = self.textCursor().selectedText()

        if selected_text:
            # plain text
            plain_text = self.textCursor().selection().toPlainText()

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            # copy to
            copy_to_menu = QMenu(trans('text.context_menu.copy_to'), self)

            # input
            action = QAction(QIcon(":/icons/input.svg"), trans('text.context_menu.copy_to.input'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.append_to_input(selected_text))
            copy_to_menu.addAction(action)

            # calendar
            action = QAction(QIcon(":/icons/schedule.svg"), trans('text.context_menu.copy_to.calendar'), self)
            action.triggered.connect(
                lambda: self.window.controller.calendar.note.append_text(selected_text))
            copy_to_menu.addAction(action)

            # notepad
            num_notepads = self.window.controller.notepad.get_num_notepads()
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    name = self.window.controller.notepad.get_notepad_name(i)
                    action = QAction(QIcon(":/icons/paste.svg"), name, self)
                    action.triggered.connect(lambda checked=False, i=i:
                                             self.window.controller.notepad.append_text(selected_text, i))
                    copy_to_menu.addAction(action)

            # python interpreter
            action = QAction(QIcon(":/icons/code.svg"), trans('text.context_menu.copy_to.python.code'), self)
            action.triggered.connect(
                lambda: self.window.controller.interpreter.append_to_edit(selected_text))
            copy_to_menu.addAction(action)
            action = QAction(QIcon(":/icons/code.svg"), trans('text.context_menu.copy_to.python.input'), self)
            action.triggered.connect(
                lambda: self.window.controller.interpreter.append_to_input(selected_text))
            copy_to_menu.addAction(action)

            menu.addMenu(copy_to_menu)

            # save as (selected)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            # save as (all)
            action = QAction(QIcon(":/icons/save.svg"), trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        menu.exec_(event.globalPos())


