#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.11 16:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout

from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class NotepadWidget(QWidget):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadWidget, self).__init__(window)
        self.window = window
        self.id = 1  # assigned in setup
        self.textarea = NotepadOutput(self.window)
        self.window.ui.nodes['tip.output.tab.notepad'] = HelpLabel(trans('tip.output.tab.notepad'), self.window)

        layout = QVBoxLayout()
        layout.addWidget(self.textarea)
        layout.addWidget(self.window.ui.nodes['tip.output.tab.notepad'])
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def setText(self, text: str):
        """
        Set text

        :param text: Text
        """
        self.textarea.setText(text)
        self.textarea.on_update()

    def toPlainText(self) -> str:
        """
        Get plain text

        :return: Plain text
        """
        return self.textarea.toPlainText()

    def on_destroy(self):
        """On destroy"""
        # unregister finder from memory
        self.window.controller.finder.unset(self.textarea.finder)


class NotepadOutput(QTextEdit):
    def __init__(self, window=None):
        """
        Notepad

        :param window: main window
        """
        super(NotepadOutput, self).__init__(window)
        self.window = window
        self.finder = Finder(window, self)
        self.setAcceptRichText(False)
        self.setStyleSheet(self.window.controller.theme.style('font.chat.output'))
        self.value = self.window.core.config.data['font_size']
        self.max_font_size = 42
        self.min_font_size = 8
        self.id = 1  # assigned in setup
        self.textChanged.connect(self.text_changed)

    def text_changed(self):
        """On text changed"""
        if not self.window.core.notepad.locked:
            self.window.controller.notepad.save(self.id)  # use notepad id
        self.finder.text_changed()

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

            # copy to (without current notepad)
            excluded_id = "notepad_id_{}".format(self.id)
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(self, selected_text, excluded=[excluded_id])
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

        action = QAction(QIcon(":/icons/search.svg"), trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec_(event.globalPos())

    def audio_read_selection(self):
        """
        Read selected text (audio)
        """
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def find_open(self):
        """Open find dialog"""
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        """On content update"""
        self.finder.clear()  # clear finder

    def keyPressEvent(self, e):
        """
        Key press event

        :param e: Event
        """
        if e.key() == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self.find_open()
        else:
            self.finder.clear(restore=True, to_end=False)
            super(NotepadOutput, self).keyPressEvent(e)

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
            super(NotepadOutput, self).wheelEvent(event)

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        self.window.controller.finder.focus_in(self.finder)
        super(NotepadOutput, self).focusInEvent(e)

    def focusOutEvent(self, e):
        """
        Focus out event

        :param e: focus event
        """
        super(NotepadOutput, self).focusOutEvent(e)
        self.window.controller.finder.focus_out(self.finder)

