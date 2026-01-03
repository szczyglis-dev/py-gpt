#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 00:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon, QKeySequence

from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor
from pygpt_net.utils import trans

class TextFileEditor(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Text file editor

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)

        self._icon_volume = QIcon(":/icons/volume.svg")
        self._icon_save = QIcon(":/icons/save.svg")
        self._icon_search = QIcon(":/icons/search.svg")

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
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

        # Add zoom submenu
        zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "editor", self.value, self.on_zoom_changed)
        menu.addMenu(zoom_menu)

        action = QAction(self._icon_search, trans('text.context_menu.find'), menu)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence.StandardKey.Find)
        menu.addAction(action)

        menu.exec_(event.globalPos())
        menu.deleteLater()