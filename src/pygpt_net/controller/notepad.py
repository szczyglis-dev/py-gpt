#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QTextCursor

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.notepad import NotepadItem
from pygpt_net.ui.widget.tabs.body import TabBody
from pygpt_net.ui.widget.textarea.notepad import NotepadWidget
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class Notepad:
    def __init__(self, window=None):
        """
        Notepad controller

        :param window: Window instance
        """
        self.window = window
        self.opened_once = False

    def create(self) -> (TabBody, int):
        """
        Create notepad widget

        :return: notepad widget (TabBody)
        """
        idx = self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD) + 1
        self.window.ui.notepad[idx] = NotepadWidget(self.window)
        self.window.ui.notepad[idx].id = idx
        self.window.ui.notepad[idx].textarea.id = idx
        title = trans('output.tab.notepad')
        title += " " + str(idx)
        children = self.window.core.tabs.from_widget(self.window.ui.notepad[idx])
        return children, idx

    def load(self):
        """Load all notepads contents"""
        self.window.core.notepad.load_all()
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if len(items) == 0:
            if num_notepads > 0:
                for idx in range(1, num_notepads + 1):
                    item = NotepadItem()
                    item.idx = idx
                    items[idx] = item

        if num_notepads > 0:
            for idx in range(1, num_notepads + 1):
                if idx not in items:
                    item = NotepadItem()
                    item.idx = idx
                    items[idx] = item
                if idx in self.window.ui.notepad:
                    self.window.ui.notepad[idx].setText(items[idx].content)

    def get_notepad_name(self, idx: int):
        """
        Get notepad name

        :param idx: notepad idx
        :return: notepad name
        """
        num = self.get_num_notepads()
        if num > 1:
            title = trans('text.context_menu.copy_to.notepad') + ' ' + str(idx)
        else:
            title = trans('text.context_menu.copy_to.notepad')
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            return None
        if item.initialized and item.title is not None and len(item.title) > 0:
            title = item.title
        return title

    def save(self, idx: int):
        """
        Save notepad contents

        :param idx: notepad idx
        """
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item

        if idx in self.window.ui.notepad:
            prev_content = item.content
            item.content = self.window.ui.notepad[idx].toPlainText()
            if prev_content != item.content:  # update only if content changed
                self.window.core.notepad.update(item)
            self.update()

    def save_all(self):
        """Save all notepads contents"""
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            tabs = self.window.core.tabs.get_tabs_by_type(Tab.TAB_NOTEPAD)
            for tab in tabs:
                idx = tab.data_id
                if idx in self.window.ui.notepad:
                    prev_content = str(items[idx].content)
                    items[idx].content = self.window.ui.notepad[idx].toPlainText()
                    # update only if content changed
                    if prev_content != items[idx].content:
                        self.window.core.notepad.update(items[idx])
            self.update()

    def setup(self):
        """Setup all notepads"""
        self.load()

    def append_text(self, text: str, idx: int):
        """
        Append text to notepad

        :param text: text to append
        :param idx: notepad idx
        """
        if idx not in self.window.ui.notepad:
            return
        dt = ""  # TODO: add to config append date/time
        # dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.notepad[idx].toPlainText()
        if prev_text.strip() != "":
            prev_text += "\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.notepad[idx].setText(new_text)
        self.save(idx)

        # move cursor to end
        cursor = self.window.ui.notepad[idx].textarea.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.window.ui.notepad[idx].textarea.setTextCursor(cursor)

    def get_num_notepads(self) -> int:
        """
        Get number of notepads

        :return: number of notepads
        """
        return self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD)

    def get_current_active(self) -> int:
        """
        Get current notepad idx

        :return: current notepad index
        """
        if self.is_active():
            tab = self.window.ui.tabs.get_current_tab()
            if tab is not None:
                return tab.data_id
        return 1

    def is_active(self) -> bool:
        """
        Check if notepad tab is active

        :return: True if notepad tab is active
        """
        return self.window.ui.tabs.get_current_type() == Tab.TAB_NOTEPAD

    def open(self):
        """Open notepad"""
        # if notepad disabled, do nothing
        if self.get_num_notepads() == 0:
            return

        # switch to first notepad tab if current tab is not notepad
        if self.window.controller.ui.tabs.get_current_type() != Tab.TAB_NOTEPAD:
            idx = self.window.core.tabs.get_min_idx_by_type(Tab.TAB_NOTEPAD)
            if idx is not None:
                self.window.ui.tabs['output'].setCurrentIndex(idx)

        self.window.activateWindow()  # focus

    def update(self):
        """Update notepads UI"""
        pass

    def reload(self):
        """Reload notepads"""
        self.window.core.notepad.locked = True
        self.window.core.notepad.reset()
        self.load()
        self.window.core.notepad.locked = False

    def switch_to_tab(self, idx: int = None):
        """
        Switch to notepad tab

        :param idx: notepad idx
        """
        if idx is None:
            idx = self.get_first_notepad_tab_idx()
        tab = self.window.core.tabs.get_tab_by_index(idx)
        if tab is not None:
            self.window.ui.tabs['output'].setCurrentIndex(idx)
        else:
            self.window.ui.tabs['output'].setCurrentIndex(self.get_first_notepad_tab_idx())

    def get_first_notepad_tab_idx(self) -> int:
        """
        Get first notepad tab index

        :return: first notepad tab index
        """
        return self.window.core.tabs.get_min_idx_by_type(Tab.TAB_NOTEPAD)

    def get_current_notepad_text(self) -> str:
        """
        Get current notepad text

        :return: current notepad text
        """
        idx = self.get_current_active()
        if idx in self.window.ui.notepad:
            return self.window.ui.notepad[idx].toPlainText()
        return ""

    def get_notepad_text(self, idx: int) -> str:
        """
        Get notepad text

        :param idx: notepad index
        :return: notepad text
        """
        if idx in self.window.ui.notepad:
            return self.window.ui.notepad[idx].toPlainText()
        return ""

    def clear(self, idx: int) -> bool:
        """
        Clear notepad contents

        :param idx: notepad idx
        """
        if idx in self.window.ui.notepad:
            self.window.ui.notepad[idx].textarea.clear()
            self.save(idx)
            return True
        return False
