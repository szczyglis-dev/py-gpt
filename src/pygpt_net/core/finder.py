#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.11 05:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor, Qt, QTextCharFormat, QTextDocument


class Finder:
    def __init__(self, window=None, textarea = None):
        """
        Finder core (in widget)

        :param window: Window instance
        :param textarea: QTextEdit / QTextBrowser (parent)
        """
        self.window = window
        self.textarea = textarea
        self.base_doc = None
        self.locked = False
        self.opened = False
        self.last_search = None
        self.matches = []
        self.current_match_index = -1
        self.type = "html"  # parent type: text | html
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.find_execute)
        self.delay = 100
        self.search_text = ""

    def set_type(self, type: str):
        """
        Set parent type (text|html)

        :param type: parent type
        """
        self.type = type

    def assign(self, textarea):
        """
        Assign parent for the finder

        :param textarea: QTextEdit / QTextBrowser
        """
        self.textarea = textarea

    def text_changed(self, doc: QTextDocument):
        """
        On parent textarea text changed

        :param doc: QTextDocument
        """
        if doc is not None:
            self.base_doc = doc.clone()
        else:
            self.base_doc = None

    def select(self):
        """Set current active"""
        current_search = self.get_search_string()
        if current_search != self.last_search:
            self.clear_search()
            self.search_text = current_search
            self.find_execute()
        else:
            if current_search is not None and len(current_search) > 0:
                self.clear_search()
                self.search_text = current_search
                self.find_execute()

    def clear_search(self):
        """Clear search state"""
        self.last_search = None
        self.matches = []
        self.current_match_index = -1
        self.reset_highlights()

    def get_search_string(self) -> str:
        """
        Get current search string

        :return: search string
        """
        return self.window.ui.nodes['dialog.find.input'].text()

    def set_doc(self, doc: QTextDocument):
        """
        Set document in the current parent

        :param doc: base document to restore
        """
        stylesheet = self.parent().styleSheet()
        self.parent().setDocument(doc)  # set document
        cursor = QTextCursor(self.parent().document())
        cursor.movePosition(QTextCursor.End)
        self.parent().setTextCursor(cursor)
        self.parent().setStyleSheet(stylesheet)  # restore stylesheet

    def get_doc(self) -> QTextDocument:
        """
        Get document from the current parent

        :return: document QTextDocument
        """
        return self.parent().document().clone()

    def clear(self, restore: bool = False, to_end: bool = True):
        """
        Clear current parent highlights

        :param restore: Restore original document
        :param to_end: Move cursor to the end
        """
        if self.get_base_doc() is not None:
            if restore:
                curr_cursor = self.parent().textCursor()
                self.set_doc(self.get_base_doc())
                if not to_end:
                    self.parent().setTextCursor(curr_cursor)
            self.clear_search()
            self.set_base_doc(None)
            if to_end:
                self.parent().moveCursor(QTextCursor.End)

    def parent(self):
        """
        Get current parent QTextEdit / QTextBrowser

        :return: QTextEdit / QTextBrowser
        """
        return self.textarea

    def set_base_doc(self, doc: QTextDocument = None):
        """
        Set original document for the current parent

        :param doc: original document
        """
        if self.type == "text":
            return
        self.base_doc = doc  # store original document

    def get_base_doc(self) -> QTextDocument:
        """
        Get original document from current parent

        :return: original document
        """
        return self.base_doc

    def prepare(self, clear: bool = True, to_end: bool = True):
        """
        Prepare the finder for a new search

        :param clear: clear search state
        :param to_end: move cursor to the end
        """
        if clear:
            self.reset(to_end)
            self.clear_search()
            self.update_current()

    def update_current(self):
        """Update the current parent original document"""
        self.set_base_doc(self.get_doc())

    def find_execute(self):
        """Execute search"""
        text = self.search_text
        self.reset_highlights()
        if self.last_search is None or text != self.last_search:
            self.prepare(clear=True, to_end=False)

        if text == self.last_search:
            self.matches = []

        if text is None or len(text) == 0:
            self.last_search = None
            self.matches = []
            self.reset_highlights()
            self.window.controller.finder.update_counter()
            return

        self.last_search = text
        self.handle_matches(text)
        if self.matches:
            if self.current_match_index < 0:
                self.find_next()

        self.window.controller.finder.update_counter()

    def find(self, text: str):
        """
        Find and highlight all occurrences of the text

        :param text: text to find
        """
        self.search_text = text
        self.timer.start(self.delay)

    def handle_matches(self, text: str):
        """
        Handle matches for the given text

        :param text: text to find
        """
        self.reset_highlights()
        self.matches = []
        parent = self.parent()
        plain_text = parent.toPlainText().lower()
        search_text = text.lower()
        pos = plain_text.find(search_text)

        while pos != -1:
            self.matches.append((pos, len(search_text)))
            pos = plain_text.find(search_text, pos + len(search_text))

        self.show_matches()

    def show_matches(self):
        """Show matches in the current parent"""
        parent = self.parent()
        cursor = QTextCursor(parent.document())
        for i, (pos, length) in enumerate(self.matches):
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
            self.highlight(cursor, i)

    def reset_highlights(self):
        """Reset highlights (text mode only)"""
        if self.type != "text":
            return

        parent = self.parent()
        cursor_position = parent.textCursor().position()

        document = parent.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()

        # Reset the character format for each block in the document
        block = document.begin()
        while block.isValid():
            cursor.setPosition(block.position())
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.setCharFormat(QTextCharFormat())
            block = block.next()

        cursor.endEditBlock()

        # Restore the original cursor position
        cursor = QTextCursor(document)
        cursor.setPosition(cursor_position)
        parent.setTextCursor(cursor)

    def find_next(self):
        """Find the next occurrence relative to the current match index"""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self.show_matches()
        self.scroll_to(self.current_match_index)

    def find_prev(self):
        """Find the previous occurrence relative to the current match"""
        if not self.matches:
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self.show_matches()
        self.scroll_to(self.current_match_index)

    def scroll_to(self, match_index: int):
        """
        Scroll to the match given by match_index

        :param match_index: current match index
        """
        parent = self.parent()
        if match_index < 0 or match_index >= len(self.matches):
            return

        pos, _ = self.matches[match_index]
        cursor = QTextCursor(parent.document())
        cursor.setPosition(pos)
        parent.setTextCursor(cursor)

    def highlight(self, cursor: QTextCursor, i: int):
        """
        Highlight the selection of the given cursor

        :param cursor: QTextCursor
        :param i: current match
        """
        fmt = cursor.charFormat()
        fmt.setForeground(Qt.black)
        current = self.current_match_index
        if current == -1:
            current = 0
        if i == current:
            fmt.setBackground(Qt.green)
        else:
            fmt.setBackground(Qt.yellow)
        cursor.setCharFormat(fmt)

    def get_scroll_position(self) -> int:
        """
        Get current scroll position

        :return: scroll position
        """
        return self.parent().verticalScrollBar().value()

    def set_scroll_position(self, value):
        """
        Set current scroll position

        :param value: scroll position
        """
        self.parent().verticalScrollBar().setValue(value)

    def restore(self):
        """Restore original document"""
        if self.get_base_doc() is not None:
            self.set_doc(self.get_base_doc())

    def reset(self, to_end: bool = True):
        """
        Reset highlights

        :param to_end: move cursor to the end
        """
        self.locked = True
        content = self.get_base_doc()
        if content is None:
            self.locked = False
            return
        now_content = self.get_doc()
        if now_content == content:
            self.locked = False
            return

        pos = self.get_scroll_position()
        self.restore()
        self.set_scroll_position(pos)

        # move cursor to end
        if to_end:
            cursor = QTextCursor(self.parent().document())
            cursor.movePosition(QTextCursor.End)
