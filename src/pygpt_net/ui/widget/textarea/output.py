#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.20 08:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextBrowser, QMenu
from PySide6.QtGui import QDesktopServices

from pygpt_net.utils import trans


class ChatOutput(QTextBrowser):
    def __init__(self, window=None):
        """
        Chat output

        :param window: main window
        """
        super(ChatOutput, self).__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.setStyleSheet(self.window.controller.theme.style('chat_output'))
        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.open_external_link)

    def open_external_link(self, url):
        """
        Open external link

        :param url: url
        """
        # local file
        if not url.scheme().startswith('http'):
            self.window.controller.files.open(url.toLocalFile())
        else:
            # external link
            QDesktopServices.openUrl(url)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        selected_text = self.textCursor().selectedText()
        if selected_text:
            # audio read
            action = menu.addAction(trans('text.context_menu.audio.read'))
            action.triggered.connect(self.audio_read_selection)

            # copy to
            copy_to_menu = QMenu(trans('text.context_menu.copy_to'), self)

            # input
            action = copy_to_menu.addAction(trans('text.context_menu.copy_to.input'))
            action.triggered.connect(
                lambda: self.window.controller.chat.render.append_text(selected_text))

            # notepad
            num_notepads = self.window.controller.notepad.get_num_notepads()
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    name = self.window.controller.notepad.get_notepad_name(i)
                    action = copy_to_menu.addAction(name)
                    action.triggered.connect(lambda checked=False, i=i:
                                             self.window.controller.notepad.append_text(selected_text, i))

            # calendar
            action = copy_to_menu.addAction(trans('text.context_menu.copy_to.calendar'))
            action.triggered.connect(
                lambda: self.window.controller.calendar.append_text(selected_text))

            menu.addMenu(copy_to_menu)
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

            self.window.core.config.data['font_size'] = self.value
            self.window.core.config.save()
            option = self.window.controller.settings.editor.get_option('font_size')
            option['value'] = self.value
            self.window.controller.config.apply('config', 'font_size', option)
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(ChatOutput, self).wheelEvent(event)
