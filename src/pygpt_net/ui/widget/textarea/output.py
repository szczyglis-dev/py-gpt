#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtGui import QAction, QIcon, QTextOption, QKeySequence

from pygpt_net.core.text.finder import Finder
from pygpt_net.utils import trans


class ChatOutput(QTextBrowser):
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    ICON_SEARCH = QIcon(":/icons/search.svg")

    def __init__(self, window=None):
        """
        Chat output

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.finder = Finder(window, self)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.setStyleSheet(self.window.controller.theme.style('font.chat.output'))
        self.value = self.window.core.config.get('font_size')
        self.max_font_size = 42
        self.min_font_size = 8
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.open_external_link)
        self.setWordWrapMode(QTextOption.WordWrap)
        self.tab = None
        self.installEventFilter(self)
        self.setProperty('class', 'layout-output-plain')
        self._auto_scroll = True
        self._auto_scroll_margin = None
        self.verticalScrollBar().valueChanged.connect(self._on_vsb_value_changed)

    def on_delete(self):
        """Clean up on delete"""
        if self.finder:
            self.finder.disconnect()
            self.finder = None

        self.tab = None
        self.clear()
        self.removeEventFilter(self)
        self.anchorClicked.disconnect(self.open_external_link)
        self.deleteLater()

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == QEvent.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def open_external_link(self, url):
        """
        Handle external link

        :param url: url
        """
        self.window.core.filesystem.url.handle(url)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()
        has_selection = cursor.hasSelection()

        if has_selection:
            selected_text = cursor.selectedText()

            action = QAction(self.ICON_VOLUME, trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text)
            menu.addMenu(copy_to_menu)

            action = QAction(self.ICON_SAVE, trans('action.save_selection_as'), self)
            action.triggered.connect(self._save_selected_text)
            menu.addAction(action)
        else:
            action = QAction(self.ICON_SAVE, trans('action.save_as'), self)
            action.triggered.connect(self._save_all_text)
            menu.addAction(action)

        action = QAction(self.ICON_SEARCH, trans('text.context_menu.find'), self)
        action.triggered.connect(self.find_open)
        action.setShortcut(QKeySequence("Ctrl+F"))
        menu.addAction(action)

        menu.exec(event.globalPos())
        menu.deleteLater()

    def _save_selected_text(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            self.window.controller.chat.common.save_text(cursor.selection().toPlainText())

    def _save_all_text(self):
        self.window.controller.chat.common.save_text(self.toPlainText())

    def audio_read_selection(self):
        """Read selected text (audio)"""
        self.window.controller.audio.read_text(self.textCursor().selectedText())

    def find_open(self):
        """Open find dialog"""
        self.window.controller.finder.open(self.finder)

    def on_update(self):
        """On content update"""
        if self.finder:
            self.finder.clear()

    def keyPressEvent(self, e):
        """
        Key press event

        :param e: Event
        """
        if e.key() == Qt.Key_F and e.modifiers() & Qt.ControlModifier:
            self.find_open()
            return
        super().keyPressEvent(e)

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            dy = event.angleDelta().y()
            if dy > 0:
                new_value = min(self.value + 1, self.max_font_size)
            elif dy < 0:
                new_value = max(self.value - 1, self.min_font_size)
            else:
                event.accept()
                return

            if new_value == self.value:
                event.accept()
                return

            self.value = new_value

            cfg = self.window.core.config
            cfg.data['font_size'] = new_value
            cfg.save()

            ctrl = self.window.controller
            option = ctrl.settings.editor.get_option('font_size')
            option['value'] = new_value
            ctrl.config.apply(parent_id='config', key='font_size', option=option)
            ctrl.ui.update_font_size()
            event.accept()
        else:
            super().wheelEvent(event)

    def focusInEvent(self, e):
        """
        Focus in event

        :param e: focus event
        """
        super().focusInEvent(e)
        self.window.controller.finder.focus_in(self.finder)

    def _calc_auto_scroll_margin(self) -> int:
        vsb = self.verticalScrollBar()
        ps = vsb.pageStep()
        if ps <= 0:
            return 2
        return max(2, min(64, ps // 10))

    def _on_vsb_value_changed(self, value: int):
        self._auto_scroll = self.was_at_bottom()

    def was_at_bottom(self) -> bool:
        vsb = self.verticalScrollBar()
        return (vsb.maximum() - vsb.value()) <= self._calc_auto_scroll_margin()

    def is_auto_scroll_enabled(self) -> bool:
        return self._auto_scroll