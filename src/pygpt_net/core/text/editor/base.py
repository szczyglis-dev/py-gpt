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

from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QActionGroup, QFont, QFontMetrics, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.textarea.zoom import local_font, queue_editor_zoom, register_editor_zoom
from pygpt_net.utils import trans

from .gutter import LINE_NUMBER_PADDING, LINE_NUMBER_TEXT_GAP, LineNumbers
from .syntax import SyntaxHighlighter


DEFAULT_TAB_WIDTH = 4
CONFIG_TAB_INDENT_SPACES = "filesystem.text_editor.tabs.indent_spaces"
CONFIG_TAB_WIDTH = "filesystem.text_editor.tabs.width"
CONFIG_WORD_WRAP = "filesystem.text_editor.word_wrap"


class TextEditor(QPlainTextEdit):
    """Shared editor behavior without feature-specific context-menu actions."""

    zoom_key = "font_size"

    def __init__(
            self,
            window=None,
            parent=None,
            path=None,
            line_numbers=True,
            syntax_highlighting=True,
            tabs=True,
    ):
        super().__init__(parent if parent is not None else window)
        self.window = window
        self.path = path
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self._tabs_enabled = bool(tabs)
        self._line_numbers_enabled = bool(line_numbers)
        self._syntax_highlighting_enabled = bool(syntax_highlighting)

        self.finder = Finder(window, self) if window is not None else None
        if self.finder is not None:
            self.textChanged.connect(self.finder.text_changed)

        self.setFont(QFont('Monaspace Neon'))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabChangesFocus(False)

        self.line_numbers = LineNumbers(self) if self._line_numbers_enabled else None
        if self.line_numbers is not None:
            self.blockCountChanged.connect(self.update_gutter)
            self.updateRequest.connect(self.update_gutter)
            self.cursorPositionChanged.connect(self.highlight_line)
            self.selectionChanged.connect(self.highlight_line)

        self.highlighter = SyntaxHighlighter(self.document(), path, self) if self._syntax_highlighting_enabled else None
        self.zoom_timer = QTimer(self)
        self.zoom_timer.setSingleShot(True)
        self.zoom_timer.setInterval(30)
        self.zoom_timer.timeout.connect(lambda: self.apply_zoom(self.value))
        self._applied_zoom = None
        self.restore_zoom()
        self.restore_word_wrap()
        self._update_tab_stop()
        self.update_gutter()

    def set_path(self, path):
        """Update the file path used for syntax lexer selection."""
        self.path = path
        if self.highlighter is not None:
            self.highlighter.set_path(path)

    def is_line_marked(self, line_number):
        """Hook for consumers such as Files annotations."""
        return False

    def update_gutter(self, *args):
        # QPlainTextEdit may dispatch resize/change events from its constructor,
        # before our Python-side helpers have been initialized.
        line_numbers = getattr(self, "line_numbers", None)
        if line_numbers is None:
            return
        digits = len(str(max(1, self.blockCount())))
        width = 2 * LINE_NUMBER_PADDING + QFontMetrics(line_numbers.number_font()).horizontalAdvance('9') * digits
        margin = width + LINE_NUMBER_TEXT_GAP
        if self.viewportMargins().left() != margin:
            self.setViewportMargins(margin, 0, 0, 0)
        rect = self.contentsRect()
        geometry = QRect(rect.left(), rect.top(), width, rect.height())
        if line_numbers.geometry() != geometry:
            line_numbers.setGeometry(geometry)
        line_numbers.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_gutter()

    def highlight_line(self):
        line_numbers = getattr(self, "line_numbers", None)
        if line_numbers is not None:
            line_numbers.update()

    def tab_width(self):
        """Return the global editor tab width, normalized to 1..8."""
        if self.window is None:
            return DEFAULT_TAB_WIDTH
        try:
            value = int(self.window.core.config.get(CONFIG_TAB_WIDTH, DEFAULT_TAB_WIDTH))
        except (TypeError, ValueError):
            value = DEFAULT_TAB_WIDTH
        return max(1, min(8, value))

    def indent_using_spaces(self):
        """Return whether editor indentation inserts spaces instead of TAB characters."""
        if self.window is None:
            return True
        return bool(self.window.core.config.get(CONFIG_TAB_INDENT_SPACES, True))

    def _save_tab_config(self, key, value):
        if self.window is None:
            return
        config = self.window.core.config
        config.set(key, value)
        config.save()

    def set_indent_using_spaces(self, enabled):
        self._save_tab_config(CONFIG_TAB_INDENT_SPACES, bool(enabled))

    def set_tab_width(self, width):
        width = max(1, min(8, int(width)))
        self._save_tab_config(CONFIG_TAB_WIDTH, width)
        self._update_tab_stop()

    def _update_tab_stop(self):
        if not getattr(self, "_tabs_enabled", False):
            return
        space_width = QFontMetrics(self.font()).horizontalAdvance(' ')
        self.setTabStopDistance(self.tab_width() * space_width)

    @staticmethod
    def _visual_column(text, tab_width):
        column = 0
        for char in text:
            if char == '\t':
                column += tab_width - (column % tab_width)
            else:
                column += 1
        return column

    def _selected_block_numbers(self, cursor):
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        first = self.document().findBlock(start).blockNumber()
        last_block = self.document().findBlock(end)
        last = last_block.blockNumber()
        if cursor.hasSelection() and end > start and end == last_block.position() and last > first:
            last -= 1
        return range(first, last + 1)

    def indent_lines(self):
        """Indent the selection/current position like a code editor."""
        cursor = self.textCursor()
        width = self.tab_width()
        if not cursor.hasSelection():
            if self.indent_using_spaces():
                block_cursor = QTextCursor(cursor)
                block_cursor.setPosition(cursor.block().position(), QTextCursor.KeepAnchor)
                before = block_cursor.selection().toPlainText()
                column = self._visual_column(before, width)
                cursor.insertText(' ' * (width - (column % width)))
            else:
                cursor.insertText('\t')
            return

        original = QTextCursor(cursor)
        prefix = ' ' * width if self.indent_using_spaces() else '\t'
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for number in self._selected_block_numbers(cursor):
            block = self.document().findBlockByNumber(number)
            if block.isValid():
                edit.setPosition(block.position())
                edit.insertText(prefix)
        edit.endEditBlock()
        self.setTextCursor(original)

    def unindent_lines(self):
        """Remove one indentation level from selected/current lines."""
        cursor = self.textCursor()
        original = QTextCursor(cursor)
        width = self.tab_width()
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for number in self._selected_block_numbers(cursor):
            block = self.document().findBlockByNumber(number)
            if not block.isValid():
                continue
            text = block.text()
            if text.startswith('\t'):
                remove = 1
            else:
                remove = min(width, len(text) - len(text.lstrip(' ')))
            if remove:
                edit.setPosition(block.position())
                edit.setPosition(block.position() + remove, QTextCursor.KeepAnchor)
                edit.removeSelectedText()
        edit.endEditBlock()
        self.setTextCursor(original)

    def convert_indentation(self, to_spaces):
        """Normalize leading indentation in the whole document."""
        width = self.tab_width()
        original = QTextCursor(self.textCursor())
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for number in range(self.document().blockCount()):
            block = self.document().findBlockByNumber(number)
            if not block.isValid():
                continue
            text = block.text()
            leading_len = len(text) - len(text.lstrip(' \t'))
            if leading_len == 0:
                continue
            leading = text[:leading_len]
            if to_spaces:
                replacement = leading.expandtabs(width)
            else:
                column = self._visual_column(leading, width)
                replacement = '\t' * (column // width) + ' ' * (column % width)
            if replacement == leading:
                continue
            edit.setPosition(block.position())
            edit.setPosition(block.position() + leading_len, QTextCursor.KeepAnchor)
            edit.insertText(replacement)
        edit.endEditBlock()
        self.setTextCursor(original)

    def get_tabs_menu(self, parent):
        menu = parent.addMenu(trans('text.editor.tabs'))

        spaces = menu.addAction(trans('text.editor.tabs.indent_spaces'))
        spaces.setCheckable(True)
        spaces.setChecked(self.indent_using_spaces())
        spaces.triggered.connect(self.set_indent_using_spaces)

        menu.addSeparator()
        group = QActionGroup(menu)
        group.setExclusive(True)
        current_width = self.tab_width()
        for width in range(1, 9):
            action = menu.addAction(trans('text.editor.tabs.width').format(width=width))
            action.setCheckable(True)
            action.setChecked(width == current_width)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, value=width: self.set_tab_width(value))

        menu.addSeparator()
        menu.addAction(trans('text.editor.tabs.convert_spaces'), lambda: self.convert_indentation(True))
        menu.addAction(trans('text.editor.tabs.convert_tabs'), lambda: self.convert_indentation(False))
        return menu


    def word_wrap_enabled(self):
        """Return whether long lines should wrap in editor-based text views."""
        if self.window is None:
            return False
        return bool(self.window.core.config.get(CONFIG_WORD_WRAP, False))

    def set_word_wrap(self, enabled):
        """Enable/disable wrapping and persist the global editor preference."""
        enabled = bool(enabled)
        if self.window is not None:
            self._save_tab_config(CONFIG_WORD_WRAP, enabled)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth if enabled else QPlainTextEdit.NoWrap)
        self.update_gutter()

    def restore_word_wrap(self):
        """Apply the persisted wrapping preference without writing config."""
        enabled = self.word_wrap_enabled()
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth if enabled else QPlainTextEdit.NoWrap)
        self.update_gutter()

    def add_word_wrap_action(self, menu):
        """Add the checkable Word wrap action to a context menu."""
        action = menu.addAction(trans('text.editor.word_wrap'))
        action.setCheckable(True)
        action.setChecked(self.lineWrapMode() != QPlainTextEdit.NoWrap)
        action.triggered.connect(self.set_word_wrap)
        return action

    def add_find_action(self, menu):
        action = menu.addAction(trans('text.context_menu.find'), self.find_open)
        return action

    def add_zoom_menu(self, menu):
        if self.window is None:
            return None
        zoom_menu = self.window.ui.context_menu.get_zoom_menu(self, "editor", self.value, self.on_zoom_changed)
        menu.addMenu(zoom_menu)
        return zoom_menu

    def restore_zoom(self):
        if self.window is None:
            self._update_tab_stop()
            return
        effective_key = self.zoom_key
        value = self.window.core.config.get(self.zoom_key)
        if not isinstance(value, (int, float)) or value <= 0:
            effective_key = 'font_size'
            value = self.window.core.config.get('font_size')
        self.value = max(self.min_font_size, min(self.max_font_size, value if isinstance(value, (int, float)) else 12))
        register_editor_zoom(self, self.window, effective_key)
        local_font(self, self.value)
        self._applied_zoom = self.value
        self._update_tab_stop()

    def apply_zoom(self, value):
        value = max(self.min_font_size, min(self.max_font_size, int(value)))
        self.value = value
        self.zoom_timer.stop()
        if self._applied_zoom == value:
            return
        local_font(self, value)
        self._applied_zoom = value
        self._update_tab_stop()
        self.update_gutter()

    def on_zoom_changed(self, value):
        if self.window is None:
            return
        queue_editor_zoom(self, self.window, value, self.zoom_key)

    def find_open(self):
        if self.window is not None and self.finder is not None:
            self.window.controller.finder.open(self.finder)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.find_open()
            event.accept()
            return
        if self._tabs_enabled and not self.isReadOnly():
            blocked = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
            if event.key() == Qt.Key_Tab and not blocked:
                self.indent_lines()
                event.accept()
                return
            if event.key() == Qt.Key_Backtab and not blocked:
                self.unindent_lines()
                event.accept()
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.window is not None and self.finder is not None:
            self.window.controller.finder.focus_in(self.finder)

    def on_update(self):
        if self.finder is not None:
            self.finder.clear()
        if self.highlighter is not None:
            self.highlighter.timer.start(0)

    def on_destroy(self):
        self.zoom_timer.stop()
        if self.finder is not None:
            self.finder.timer.stop()
            try:
                self.textChanged.disconnect(self.finder.text_changed)
            except (RuntimeError, TypeError):
                pass
            if self.window is not None:
                self.window.controller.finder.unset(self.finder)
            self.finder.disconnect()
        if self.highlighter is not None:
            self.highlighter.timer.stop()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.on_zoom_changed(self.value + (1 if delta > 0 else -1))
            event.accept()
        else:
            super().wheelEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.restore_zoom()
        highlighter = getattr(self, "highlighter", None)
        if highlighter is not None:
            highlighter.refresh()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange, QEvent.ApplicationPaletteChange, QEvent.FontChange):
            self.update_gutter()
            self.highlight_line()
            self._update_tab_stop()
            highlighter = getattr(self, "highlighter", None)
            if highlighter is not None:
                highlighter.timer.start(0)
