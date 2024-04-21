#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.20 06:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor, Qt
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QTextEdit


class WebFinder:
    def __init__(self, window=None, textarea = None):
        """
        Finder core (in widget)

        :param window: Window instance
        :param textarea: QTextEdit / QTextBrowser (parent)
        """
        self.window = window
        self.textarea = textarea
        self.last_search = None
        self.matches = 0
        self.current_match_index = 0
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.find_execute)
        self.delay = 100
        self.search_text = ""

    def assign(self, textarea):
        """
        Assign parent for the finder

        :param textarea: QTextEdit / QTextBrowser
        """
        self.textarea = textarea

    def text_changed(self):
        """On parent textarea text changed"""
        self.reset_highlights()

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
        self.matches = 0
        self.current_match_index = 0
        self.reset_highlights()

    def get_search_string(self) -> str:
        """
        Get current search string

        :return: search string
        """
        return self.window.ui.nodes['dialog.find.input'].text()

    def clear(self, restore: bool = False, to_end: bool = True):
        """
        Clear current parent highlights

        :param restore: Restore original document
        :param to_end: Move cursor to the end
        """
        self.clear_search()

    def parent(self):
        """
        Get current parent QTextEdit / QTextBrowser

        :return: QTextEdit / QTextBrowser
        """
        return self.textarea

    def prepare(self, clear: bool = True):
        """
        Prepare the finder for a new search

        :param clear: clear search state
        """
        if clear:
            self.clear_search()

    def find_execute(self):
        """Execute search"""
        text = self.search_text
        self.reset_highlights()
        if self.last_search is None or text != self.last_search:
            self.prepare()

        if text == self.last_search:
            self.matches = 0

        if text is None or len(text) == 0:
            self.last_search = None
            self.matches = 0
            self.reset_highlights()
            self.window.controller.finder.update_counter()
            return

        self.last_search = text
        self.handle_matches(text)
        if self.matches > 0:
            if self.current_match_index < 0:
                self.find_next()

        self.window.controller.finder.update_counter()

    def on_find_finished(self):
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
        parent = self.parent()
        parent.findText(text)

    def show_matches(self):
        """Show matches in the current parent"""
        return
        self.reset_highlights()  # Clear existing highlights
        parent = self.parent()

        cursor = QTextCursor(self.textarea.document())
        extra_selections = []
        current = self.current_match_index
        if current == -1:
            current = 0
        i = 0
        for start, length in self.matches:
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)
            selection = QTextEdit.ExtraSelection()
            selection.format.setForeground(Qt.black)
            if i == current:
                selection.format.setBackground(Qt.green)
            else:
                selection.format.setBackground(Qt.yellow)
            selection.cursor = cursor
            extra_selections.append(selection)
            i += 1

        self.textarea.setExtraSelections(extra_selections)

    def reset_highlights(self):
        """Reset all highlights."""
        parent = self.parent()
        parent.findText("")

    def find_next(self):
        """Find the next occurrence relative to the current match index"""
       # self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        parent = self.parent()
        parent.findText(self.search_text)

    def find_prev(self):
        """Find the previous occurrence relative to the current match index"""
        if not self.matches:
            pass
            #return

        #self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        parent = self.parent()
        parent.findText(self.search_text, QWebEnginePage.FindBackward)
        #self.scroll_to(self.current_match_index)

    def scroll_to(self, match_index: int):
        """
        Scroll to the match given by match index

        :param match_index: current match index
        """
        return
        parent = self.parent()
        if match_index < 0 or match_index >= len(self.matches):
            return

        pos, _ = self.matches[match_index]
        cursor = QTextCursor(parent.document())
        cursor.setPosition(pos)
        parent.setTextCursor(cursor)
