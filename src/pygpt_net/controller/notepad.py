#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

import datetime

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.utils import trans


class Notepad:
    def __init__(self, window=None):
        """
        Notepad controller

        :param window: Window instance
        """
        self.window = window
        self.default_num_notepads = 3
        self.start_tab_idx = 3  # tab idx from notepad starts

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
                    title = items[idx].title
                    self.window.ui.notepad[idx].setText(items[idx].content)
                    if items[idx].initialized and title is not None and len(title) > 0:
                        self.update_name(idx, items[idx].title, False)

    def reload_tab_names(self):
        """Reload tab names (after lang change)"""
        items = self.window.core.notepad.get_all()
        for idx in items:
            title = items[idx].title
            if items[idx].initialized and title is not None and len(title) > 0:
                self.update_name(idx, items[idx].title, False)

    def get_notepad_name(self, idx: int):
        """
        Get notepad name

        :param idx: notepad idx
        :return: notepad name
        """
        title = trans('text.context_menu.copy_to.notepad') + ' ' + str(idx)
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            return None
        if item.initialized and item.title is not None and len(item.title) > 0:
            title = item.title
        return title

    def rename(self, idx: int):
        """
        Rename tab

        :param idx: notepad index (real, not tab idx)
        """
        # get attachment object by ID
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'notepad'
        self.window.ui.dialog['rename'].input.setText(item.title)
        self.window.ui.dialog['rename'].current = idx
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, idx: int, name: str, close: bool = True):
        """
        Update notepad title

        :param idx: notepad idx
        :param name: notepad name
        :param close: close dialog
        """
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item

        tab_idx = idx + (self.start_tab_idx - 1)  # calculate tab idx
        if name is None or len(name) == 0:
            self.window.ui.tabs['output'].setTabText(tab_idx, trans('output.tab.notepad') + " " + str(idx))
            item.title = ""
            item.initialized = False
        else:
            self.window.ui.tabs['output'].setTabText(tab_idx, name)
            item.title = name
            item.initialized = True
        self.window.core.notepad.update(item)
        if close:
            self.window.ui.dialog['rename'].close()

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
            for idx in range(1, num_notepads + 1):
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
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.notepad[idx].setText(new_text)
        self.save(idx)

    def get_num_notepads(self) -> int:
        """
        Get number of notepads

        :return: number of notepads
        :rtype: int
        """
        return self.window.core.config.get('notepad.num') or self.default_num_notepads

    def rename_upd(self, idx: int, name: str):
        """
        Rename notepad

        :param idx: notepad idx
        :param name: new notepad name
        """
        item = self.window.core.notepad.get_by_id(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            self.window.core.notepad.items[idx] = item
        item.title = name
        self.window.core.notepad.update(item)
        self.update()

    def update(self):
        """Update notepads UI"""
        pass
