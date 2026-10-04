#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 10:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon, QKeySequence

from pygpt_net.core.text.editor import TextEditor
from pygpt_net.utils import trans


class TextFileEditor(TextEditor):
    def __init__(self, window=None):
        """Text file editor using the shared code-editor core."""
        super().__init__(
            window=window,
            parent=window,
            path=None,
            line_numbers=True,
            syntax_highlighting=True,
            tabs=True,
        )
        self.window = window
        self.setReadOnly(True)
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""

        self._icon_volume = QIcon(":/icons/volume.svg")
        self._icon_save = QIcon(":/icons/save.svg")
        self._icon_search = QIcon(":/icons/search.svg")

    def update_stylesheet(self, data: str):
        self.setStyleSheet(self.default_stylesheet + data)
        self.restore_zoom()

    def audio_read_selection(self):
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def contextMenuEvent(self, event):
        """Context menu event."""
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()

        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            plain_text = cursor.selection().toPlainText()

            action = QAction(self._icon_volume, trans('text.context_menu.audio.read'), menu)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text)
            menu.addMenu(copy_to_menu)

            action = QAction(self._icon_save, trans('action.save_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text)
            )
            menu.addAction(action)
        else:
            action = QAction(self._icon_save, trans('action.save_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText())
            )
            menu.addAction(action)

        datetime_menu = self.window.ui.context_menu.get_insert_datetime_menu(menu, self)
        menu.addMenu(datetime_menu)

        action = self.add_find_action(menu)
        action.setIcon(self._icon_search)
        action.setShortcut(QKeySequence.StandardKey.Find)
        self.get_tabs_menu(menu)
        self.add_zoom_menu(menu)
        menu.addSeparator()
        self.add_word_wrap_action(menu)

        menu.exec(event.globalPos())
        menu.deleteLater()
