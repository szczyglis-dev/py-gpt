#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.08 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QTextCursor, Qt


class Finder:
    def __init__(self, window=None):
        """
        Finder controller

        :param window: Window instance
        """
        self.window = window
        self.original_html = {}
        self.id = None
        self.locked = False
        self.opened = False
        self.last_search = {}
        self.matches = {}
        self.current_match_index = {}

    def set_active(self, id):
        """
        Set current active parent id

        :param id: parent id
        """
        self.id = id
        current_search = self.get_search_string()
        if self.id in self.last_search:
            if current_search != self.last_search[self.id]:
                self.clear_search(self.id)
                self.find(current_search)
        else:
            if current_search is not None and len(current_search) > 0:
                self.clear_search(self.id)
                self.find(current_search)
        self.update_counter()

    def clear_search(self, id):
        """
        Clear search state for a specific id

        :param id: parent id
        """
        self.last_search[id] = None
        self.matches[id] = []
        self.current_match_index[id] = -1
        self.update_counter()

    def get_search_string(self):
        """
        Get last search string

        :return: search string
        """
        return self.window.ui.nodes['dialog.find.input'].text()

    def open(self, id):
        """
        Open finder dialog

        :param id: parent id
        """
        if self.opened:
            return
        self.set_active(id)
        self.prepare(clear=False)
        self.window.ui.dialog['find'].show()
        self.opened = True
        self.window.ui.nodes['dialog.find.input'].setFocus()
        current = self.get_search_string()
        if current is not None and len(current) > 0:
            self.window.controller.finder.find(current)

    def close(self, reset: bool = True):
        """
        Close finder dialog

        :param reset: Reset highlights
        """
        if reset:
            self.reset()
        self.window.ui.dialog['find'].hide()
        self.opened = False

    def clear(self, id: str, restore: bool = False, to_end: bool = True):
        """
        Clear current parent highlights

        :param id: parent id
        :param restore: Restore original HTML
        :param to_end: Move cursor to the end
        """
        if id in self.original_html:
            if restore:
                curr_cursor = self.get_current_parent().textCursor()
                self.get_current_parent().setHtml(self.original_html[id])
                if not to_end:
                    self.get_current_parent().setTextCursor(curr_cursor)
            del self.original_html[id]
            self.clear_search(id)
            if to_end:
                self.get_current_parent().moveCursor(QTextCursor.End)
        self.update_counter()

    def clear_input(self):
        """Clear input text"""
        self.window.ui.nodes['dialog.find.input'].clear()
        self.find("")

    def get_current_parent(self):
        """
        Get current parent QTextEdit / QTextBrowser

        :return: QTextEdit / QTextBrowser
        """
        if self.id is not None:
            if self.id == "chat_output":
                return self.window.ui.nodes['output']
            elif self.id.startswith("notepad_"):
                idx = int(self.id.split("_")[1])
                return self.window.ui.notepad[idx].textarea

    def get_original_html(self) -> str:
        """
        Get original HTML for the current parent

        :return: original HTML
        """
        if self.id is not None:
            if self.id in self.original_html:
                return self.original_html[self.id]

    def update_counter(self):
        """Update counter for current parent"""
        if not self.opened:
            return
        if self.id is not None:
            current = self.current_match_index[self.id] + 1 if self.current_match_index.get(self.id, -1) >= 0 else 0
            all = len(self.matches.get(self.id, []))
            self.window.ui.nodes['dialog.find.counter'].setText("{}/{}".format(current, all))
        else:
            self.window.ui.nodes['dialog.find.counter'].setText("0/0")
    def prepare(self, clear: bool = True, to_end: bool = True):
        """
        Prepare the finder for a new search

        :param clear: clear search state
        :param to_end: move cursor to the end
        """
        if self.id not in self.matches:
            self.matches[self.id] = []
        if self.id not in self.current_match_index:
            self.current_match_index[self.id] = -1

        # reset highlights and clear search state
        if clear:
            self.reset(to_end)
            self.clear_search(self.id)
            self.update_current()

    def update_current(self):
        """Update the current parent original HTML"""
        self.original_html[self.id] = self.get_current_parent().toHtml()

    def find(self, text: str):
        """
        Find and highlight all occurrences of the text

        :param text: text to find
        """
        if self.id not in self.last_search or text != self.last_search.get(self.id, None):
            self.prepare(clear=True, to_end=False)

        if text == self.last_search.get(self.id, None):
            self.matches[self.id] = []

        if text is None or len(text) == 0:
            self.last_search[self.id] = None
            self.matches[self.id] = []
            return

        self.last_search[self.id] = text
        parent = self.get_current_parent()

        # make regex safe search string:
        text = QRegularExpression.escape(text)

        # use QTextCursor for searching
        cursor = QTextCursor(parent.document())
        regex = QRegularExpression(text, QRegularExpression.CaseInsensitiveOption)
        plain_text = parent.toPlainText()
        index = regex.match(plain_text)

        # highlight and store all matches
        while index.hasMatch():
            pos = index.capturedStart()
            length = index.capturedLength()
            self.matches[self.id].append((pos, length))  # save position and length of match
            cursor.setPosition(pos)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
            self.highlight(cursor)
            index = regex.match(plain_text, pos + length)

        self.update_counter()
        if self.matches[self.id] and self.id in self.current_match_index:
            idx = self.current_match_index[self.id]
            if idx < 0:
                self.find_next()

    def find_next(self):
        """Find the next occurrence relative to the current match index for the active id"""
        if not self.matches.get(self.id, []):
            return

        self.current_match_index[self.id] = (self.current_match_index[self.id] + 1) % len(self.matches[self.id])
        self.scroll(self.id, self.current_match_index[self.id])
        self.update_counter()

    def find_prev(self):
        """Find the previous occurrence relative to the current match index for the active id"""
        if not self.matches.get(self.id, []):
            return

        self.current_match_index[self.id] = (self.current_match_index[self.id] - 1) % len(self.matches[self.id])
        self.scroll(self.id, self.current_match_index[self.id])
        self.update_counter()

    def scroll(self, id: str, match_index: int):
        """
        Scroll to the match given by match_index for the specified id

        :param id: str
        :param match_index: int
        """
        parent = self.get_current_parent()
        if match_index < 0 or match_index >= len(self.matches[id]):
            return

        pos, _ = self.matches[id][match_index]
        cursor = QTextCursor(parent.document())
        cursor.setPosition(pos)
        parent.setTextCursor(cursor)

    def highlight(self, cursor):
        """
        Highlight the selection of the given cursor

        :param cursor: QTextCursor
        """
        fmt = cursor.charFormat()
        fmt.setForeground(Qt.black)
        fmt.setBackground(Qt.yellow)
        cursor.setCharFormat(fmt)

    def get_current_scroll_position(self):
        """
        Get current scroll position

        :return: scroll position
        """
        return self.get_current_parent().verticalScrollBar().value()

    def set_current_scroll_position(self, value):
        """
        Set current scroll position

        :param value: scroll position
        """
        self.get_current_parent().verticalScrollBar().setValue(value)

    def reset(self, to_end: bool = True):
        """
        Reset highlights

        :param to_end: move cursor to the end
        """
        self.locked = True
        html = self.get_original_html()
        if html is None:
            self.locked = False
            return
        now_html = self.get_current_parent().toHtml()
        if now_html == html:
            self.locked = False
            return

        pos = self.get_current_scroll_position()
        self.get_current_parent().setHtml(self.get_original_html())
        self.set_current_scroll_position(pos)

        # move cursor to end
        if to_end:
            cursor = QTextCursor(self.get_current_parent().document())
            cursor.movePosition(QTextCursor.End)
