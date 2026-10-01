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


class DialogTextEditor(TextEditor):
    """General-purpose code/text editor for application dialogs."""

    _ICON_VOLUME = QIcon(":/icons/volume.svg")
    _ICON_SAVE = QIcon(":/icons/save.svg")
    _ICON_SEARCH = QIcon(":/icons/search.svg")
    _ICON_CLOSE = QIcon(":/icons/close.svg")
    _FIND_SEQ = QKeySequence("Ctrl+F")

    def __init__(self, window=None, path=None):
        super().__init__(
            window=window,
            parent=window,
            path=path,
            line_numbers=True,
            syntax_highlighting=True,
            tabs=True,
        )
        self.window = window
        self.setReadOnly(True)
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.excluded_copy_to = []

    def update_stylesheet(self, data: str):
        self.setStyleSheet(self.default_stylesheet + data)
        self.restore_zoom()

    def clear_content(self):
        self.clear()

    def audio_read_selection(self):
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()
        selected_text = cursor.selectedText()

        if selected_text:
            plain_text = cursor.selection().toPlainText()

            action = QAction(self._ICON_VOLUME, trans('text.context_menu.audio.read'), menu)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(
                menu,
                selected_text,
                excluded=self.excluded_copy_to,
            )
            try:
                copy_to_menu.setParent(menu)
            except Exception:
                pass
            menu.addMenu(copy_to_menu)

            action = QAction(self._ICON_SAVE, trans('action.save_selection_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text)
            )
            menu.addAction(action)
        else:
            action = QAction(self._ICON_SAVE, trans('action.save_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText())
            )
            menu.addAction(action)

        action = self.add_find_action(menu)
        action.setIcon(self._ICON_SEARCH)
        action.setShortcut(self._FIND_SEQ)
        self.get_tabs_menu(menu)
        self.add_zoom_menu(menu)

        action = QAction(self._ICON_CLOSE, trans('action.clear'), menu)
        action.triggered.connect(self.clear_content)
        menu.addAction(action)

        menu.addSeparator()
        self.add_word_wrap_action(menu)

        menu.exec(event.globalPos())
        menu.deleteLater()
