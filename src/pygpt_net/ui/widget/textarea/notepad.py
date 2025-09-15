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

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QTextCursor, QFontMetrics
from PySide6.QtWidgets import QTextEdit, QWidget, QVBoxLayout

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans


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
        self.opened = False
        self.tab = None

        layout = QVBoxLayout()
        layout.addWidget(self.textarea)
        layout.addWidget(self.window.ui.nodes['tip.output.tab.notepad'])
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setProperty('class', 'layout-notepad')

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab
        self.textarea.set_tab(tab)

    def scroll_to_bottom(self):
        """Scroll down"""
        self.textarea.scroll_to_bottom()

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
    def on_delete(self):
        """On delete"""
        self.tab = None  # clear tab reference
        self.textarea.on_delete()  # delete textarea
        self.deleteLater()

class NotepadOutput(QTextEdit):
    ICON_VOLUME = QIcon(":/icons/volume.svg")
    ICON_SAVE = QIcon(":/icons/save.svg")
    ICON_SEARCH = QIcon(":/icons/search.svg")

    def __init__(self, window=None):
        """
        Notepad output textarea

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
        self.tab = None
        self.last_scroll_pos = None
        self.installEventFilter(self)
        self.setProperty('class', 'layout-notepad')

        metrics = QFontMetrics(self.font())
        space_width = metrics.horizontalAdvance(" ")
        self.setTabStopDistance(4 * space_width)

        self._vscroll = self.verticalScrollBar()
        self._vscroll.valueChanged.connect(self._on_scrollbar_value_changed)
        self._restore_attempts = 0

    def on_delete(self):
        """On delete"""
        if self.finder:
            self.finder.disconnect()  # disconnect finder
            self.finder = None  # delete finder
        self.deleteLater()

    def showEvent(self, event):
        super().showEvent(event)
        self._restore_attempts = 0
        QTimer.singleShot(0, self.restore_scroll_pos)

    def scroll_to_bottom(self):
        self.moveCursor(QTextCursor.End)
        self.ensureCursorVisible()
        scroll_bar = self._vscroll
        scroll_bar.setValue(scroll_bar.maximum())

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

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def setText(self, text: str):
        if self.toPlainText() == text:
            return
        self.setPlainText(text)

    def text_changed(self):
        """On text changed"""
        if not self.window.core.notepad.locked:
            self.window.controller.notepad.save(self.id)  # use notepad id
        if self.finder is not None:
            self.finder.text_changed()
        self.last_scroll_pos = self._vscroll.value()

    def _on_scrollbar_value_changed(self, value: int):
        self.last_scroll_pos = value

    def restore_scroll_pos(self):
        if self.last_scroll_pos is None:
            return
        scroll_bar = self._vscroll
        current_max = scroll_bar.maximum()
        if self.last_scroll_pos > current_max:
            if self._restore_attempts < 30:
                self._restore_attempts += 1
                QTimer.singleShot(16, self.restore_scroll_pos)
            else:
                scroll_bar.setValue(current_max)
        else:
            scroll_bar.setValue(self.last_scroll_pos)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        menu = self.createStandardContextMenu()
        cursor = self.textCursor()
        selected_text = cursor.selectedText()
        if selected_text:
            plain_text = cursor.selection().toPlainText()

            action = QAction(self.ICON_VOLUME, trans('text.context_menu.audio.read'), self)
            action.triggered.connect(self.audio_read_selection)
            menu.addAction(action)

            excluded_id = f"notepad_id_{self.id}"
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected_text, excluded=[excluded_id])
            menu.addMenu(copy_to_menu)

            action = QAction(self.ICON_SAVE, trans('action.save_selection_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(plain_text))
            menu.addAction(action)
        else:
            action = QAction(self.ICON_SAVE, trans('action.save_as'), self)
            action.triggered.connect(
                lambda: self.window.controller.chat.common.save_text(self.toPlainText()))
            menu.addAction(action)

        action = QAction(self.ICON_SEARCH, trans('text.context_menu.find'), self)
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
            delta = event.angleDelta().y()
            if delta > 0:
                if self.value < self.max_font_size:
                    self.value += 1
                else:
                    return
            else:
                if self.value > self.min_font_size:
                    self.value -= 1
                else:
                    return

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
            self.last_scroll_pos = self._vscroll.value()
        else:
            super(NotepadOutput, self).wheelEvent(event)
            self.last_scroll_pos = self._vscroll.value()

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