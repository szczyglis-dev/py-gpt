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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QFontMetrics
from PySide6.QtWidgets import QTextEdit

from pygpt_net.core.text.finder import Finder
from pygpt_net.utils import trans


class BaseCodeEditor(QTextEdit):

    _ICON_VOLUME = QIcon(":/icons/volume.svg")
    _ICON_SAVE = QIcon(":/icons/save.svg")
    _ICON_SEARCH = QIcon(":/icons/search.svg")
    _ICON_CLOSE = QIcon(":/icons/close.svg")
    _FIND_SEQ = QKeySequence("Ctrl+F")

    def __init__(self, window=None):
        """
        Base code editor

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.finder = Finder(window, self)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'code-editor')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.excluded_copy_to = []
        self.textChanged.connect(self.text_changed)

        metrics = QFontMetrics(self.font())
        space_width = metrics.horizontalAdvance(" ")
        self.setTabStopDistance(4 * space_width)

    def text_changed(self):
        self.finder.text_changed()

    def update_stylesheet(self, data: str):
        self.setStyleSheet(self.default_stylesheet + data)

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
                excluded=self.excluded_copy_to
            )
            try:
                copy_to_menu.setParent(menu)
            except Exception:
                pass
            menu.addMenu(copy_to_menu)

            action = QAction(self._ICON_SAVE, trans('action.save_selection_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            action = QAction(self._ICON_SAVE, trans('action.save_as'), menu)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        # Add zoom submenu
        zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "editor", self.value, self.on_zoom_changed)
        menu.addMenu(zoom_menu)

        action = QAction(self._ICON_SEARCH, trans('text.context_menu.find'), menu)
        action.triggered.connect(self.find_open)
        action.setShortcut(self._FIND_SEQ)
        menu.addAction(action)

        action = QAction(self._ICON_CLOSE, trans('action.clear'), menu)
        action.triggered.connect(self.clear_content)
        menu.addAction(action)

        menu.exec(event.globalPos())
        menu.deleteLater()

    def clear_content(self):
        self.clear()

    def audio_read_selection(self):
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def find_open(self):
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        self.finder.clear()

    def on_destroy(self):
        self.window.controller.finder.unset(self.finder)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self.find_open()
        else:
            super().keyPressEvent(e)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            prev = self.value
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            if self.value != prev:
                self.update_stylesheet(f"QTextEdit {{ font-size: {self.value}px }};")
            event.accept()
        else:
            super().wheelEvent(event)

    def on_zoom_changed(self, value: int):
        """
        On font size changed

        :param value: New font size
        """
        self.value = value
        self.update_stylesheet(f"QTextEdit {{ font-size: {value}px }};")

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)


class CodeEditor(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Code editor

        :param window: main window
        """
        super().__init__(window)