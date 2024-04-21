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


class Finder:
    def __init__(self, window=None):
        """
        Finder controller

        :param window: Window instance
        """
        self.window = window
        self.parent = None
        self.locked = False
        self.opened = False

    def clear_search(self):
        """Clear search state"""
        if self.parent is not None:
            self.parent.clear_search()
        self.update_counter()

    def focus_input(self, text: str):
        """
        On focus in search string input

        :param text: search string
        """
        if text is not None and len(text) > 0:
            if self.parent is not None:
                self.parent.find(text)
        self.update_counter()

    def focus_in(self, parent):
        """
        On focus in parent

        :param parent: parent
        """
        self.set(parent)
        self.update_counter()

    def focus_out(self, parent):
        """
        On focus out parent

        :param parent: parent
        """
        pass

    def search_text_changed(self, search_string: str):
        """
        On search input text changed

        :param search_string: search string
        """
        if self.parent is not None:
            self.parent.find(search_string)
        self.update_counter()

    def prev(self):
        """Find previous match"""
        if self.parent is not None:
            self.parent.find_prev()
        self.update_counter()

    def next(self):
        """Find next match"""
        if self.parent is not None:
            self.parent.find_next()
        self.update_counter()

    def get_search_string(self):
        """
        Get current search string from input

        :return: search string
        """
        return self.window.ui.nodes['dialog.find.input'].text()

    def set(self, parent):
        """
        Set current parent for the finder

        :param parent: parent
        """
        self.parent = parent

    def unset(self, parent):
        """
        Unset parent from the finder

        :param parent: parent
        """
        if self.parent == parent:
            self.parent = None

    def open(self, parent):
        """
        Open finder dialog

        :param parent: parent finder
        """
        self.parent = parent
        if self.opened:
            self.window.ui.nodes['dialog.find.input'].setFocus()
            return
        if self.parent is not None:
            self.parent.prepare(clear=False)
        self.window.ui.dialog['find'].show()
        self.opened = True
        self.window.ui.nodes['dialog.find.input'].setFocus()
        current = self.get_search_string()
        if current is not None and len(current) > 0:
            if self.parent is not None:
                self.parent.find(current)

    def close(self, reset: bool = True):
        """
        Close finder dialog

        :param reset: Reset highlights
        """
        if reset and self.parent is not None:
            self.parent.reset()
        self.window.ui.dialog['find'].hide()
        self.opened = False

    def clear(self, restore: bool = False, to_end: bool = True):
        """
        Clear current parent highlights

        :param restore: Restore original content
        :param to_end: Move cursor to the end
        """
        if self.parent is not None:
            self.parent.clear(restore, to_end)
        self.update_counter()

    def clear_input(self):
        """Clear input text"""
        self.window.ui.nodes['dialog.find.input'].clear()
        if self.parent is not None:
            self.parent.find("")

    def update_counter(self):
        """Update counter for current parent"""
        if not self.opened:
            return
        self.window.ui.nodes['dialog.find.counter'].setText("0/0")
        if self.parent is None:
            return
        current = 0
        total_found = 0
        if isinstance(self.parent.matches, list):
            current = self.parent.current_match_index + 1 if self.parent.current_match_index >= 0 else 0
            total_found = len(self.parent.matches)
        elif isinstance(self.parent.matches, int):
            current = self.parent.current_match_index if self.parent.current_match_index >= 0 else 0
            total_found = self.parent.matches
        self.window.ui.nodes['dialog.find.counter'].setText("{}/{}".format(current, total_found))
