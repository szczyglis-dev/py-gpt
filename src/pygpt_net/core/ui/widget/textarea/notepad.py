#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTextEdit, QMenu

from ....utils import trans


class NotepadOutput(QTextEdit):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.setStyleSheet(self.window.controller.theme.get_style('chat_output'))
        self.value = self.window.app.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.no = 0

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
                lambda: self.window.controller.input.append_text(selected_text))

            # notepad
            num_notepads = self.window.controller.notepad.get_num_notepads()
            if num_notepads > 0:
                for i in range(1, num_notepads + 1):
                    if i == self.no:
                        continue
                    action = copy_to_menu.addAction(trans('text.context_menu.copy_to.notepad') + ' ' + str(i))
                    action.triggered.connect(lambda checked=False, i=i:
                                             self.window.controller.notepad.append_text(selected_text, i))

            menu.addMenu(copy_to_menu)
        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """
        Read selected text (audio)
        """
        self.window.controller.output.speech_selected_text(self.textCursor().selectedText())

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(NotepadOutput, self).keyPressEvent(event)
        self.window.controller.notepad.save(self.no)

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

            self.window.app.config.data['font_size'] = self.value
            self.window.app.config.save()
            self.window.controller.settings.update_font_size()
            event.accept()
        else:
            super(NotepadOutput, self).wheelEvent(event)
