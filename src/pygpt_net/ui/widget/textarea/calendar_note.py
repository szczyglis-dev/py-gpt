#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 05:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit, QMenu

from pygpt_net.utils import trans


class CalendarNote(QTextEdit):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(CalendarNote, self).__init__(window)
        self.window = window
        self.setAcceptRichText(False)
        self.setStyleSheet(self.window.controller.theme.style('chat_output'))
        self.value = int(self.window.core.config.get('font_size.calendar.note') or 12)
        self.textChanged.connect(self.window.controller.calendar.update_note)
        self.max_font_size = 42
        self.min_font_size = 8

    def contextMenuEvent(self, event):
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

            menu.addMenu(copy_to_menu)
        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """
        Read selected text (audio)
        """
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

            self.window.core.config.data['font_size.calendar.note'] = self.value
            self.window.core.config.save()
            self.window.controller.ui.update_font_size()
            event.accept()
        else:
            super(CalendarNote, self).wheelEvent(event)
