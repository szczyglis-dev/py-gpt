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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPlainTextEdit

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
        self.excluded_copy_to = []

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
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(
                self,
                selected_text,
                excluded=self.excluded_copy_to
            )
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
