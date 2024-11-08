#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.08 22:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QImage
from PySide6.QtWidgets import QTextEdit, QApplication

from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        self.value = self.window.core.config.data['font_size.input']
        self.max_font_size = 42
        self.min_font_size = 8
        self.textChanged.connect(self.window.controller.ui.update_tokens)

    def insertFromMimeData(self, source):
        """
        Insert from mime data

        :param source: source
        """
        self.handle_clipboard(source)
        if not source.hasImage():
            super().insertFromMimeData(source)

    def handle_clipboard(self, source):
        """
        Handle clipboard

        :param source: source
        """
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
        elif source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path)
        elif source.hasText():
            text = source.text()
            self.window.controller.attachment.from_clipboard_text(text)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: event
        """
        menu = self.createStandardContextMenu()

        # paste attachment
        if self.window.controller.attachment.clipboard_has_attachment():
            action = QAction(QIcon(":/icons/paste.svg"), trans("action.use.attachment"), self)
            action.triggered.connect(self.action_from_clipboard)
            menu.addAction(action)

        selected_text = self.textCursor().selectedText()
        if selected_text:
            # plain text
            plain_text = self.textCursor().selection().toPlainText()

            # audio read
            action = QAction(QIcon(":/icons/volume.svg"), trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            # copy to
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(self, selected_text, excluded=["input"])
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

        try:
            self.window.core.prompt.template.to_menu_options(menu, "input")
            self.window.core.prompt.custom.to_menu_options(menu, "input")
        except Exception as e:
            self.window.core.debug.log(e)

        # save current prompt
        action = QAction(QIcon(":/icons/save.svg"), trans('preset.prompt.save_custom'), self)
        action.triggered.connect(self.window.controller.presets.save_prompt)
        menu.addAction(action)

        menu.exec_(event.globalPos())

    def action_from_clipboard(self):
        """
        Get from clipboard
        """
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        self.handle_clipboard(source)

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(ChatInput, self).keyPressEvent(event)
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:  # Enter or Shift + Enter
                if mode == 2:  # Shift + Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier or modifiers == QtCore.Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                else:  # Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers != QtCore.Qt.ShiftModifier and modifiers != QtCore.Qt.ControlModifier:
                        self.window.controller.chat.input.send_input()
                self.setFocus()

        # cancel edit
        elif event.key() == Qt.Key_Escape and self.window.controller.ctx.extra.is_editing():
            self.window.controller.ctx.extra.edit_cancel()

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
            super(ChatInput, self).wheelEvent(event)
