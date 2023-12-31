#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
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
        self.default_num_notepads = 5

    def load(self):
        """Load all notepads contents"""
        self.window.core.notepad.load_all()
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if len(items) == 0:
            if num_notepads > 0:
                for id in range(1, num_notepads + 1):
                    item = NotepadItem()
                    item.id = id
                    items[id] = item

        if num_notepads > 0:
            for id in range(1, num_notepads + 1):
                if id not in items:
                    item = NotepadItem()
                    item.id = id
                    items[id] = item
                if id in self.window.ui.notepad:
                    title = items[id].title
                    self.window.ui.notepad[id].setText(items[id].content)
                    if items[id].initialized and title is not None and len(title) > 0:
                        self.update_name(id, items[id].title, False)

    def reload_tab_names(self):
        """Reload tab names (after lang change)"""
        items = self.window.core.notepad.get_all()
        for id in items:
            title = items[id].title
            if items[id].initialized and title is not None and len(title) > 0:
                self.update_name(id, items[id].title, False)

    def rename(self, idx: int):
        """
        Rename tab

        :param idx: tab index
        """
        # get notepad ID
        id = idx - 1

        # get attachment object by ID
        item = self.window.core.notepad.get_by_id(id)
        if item is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'notepad'
        self.window.ui.dialog['rename'].input.setText(item.title)
        self.window.ui.dialog['rename'].current = id
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, id: int, name: str, close: bool = True):
        """
        Update notepad title

        :param id: notepad id
        :param name: notepad name
        :param close: close dialog
        """
        item = self.window.core.notepad.get_by_id(id)
        if item is None:
            item = NotepadItem()
            item.id = id
            self.window.core.notepad.items[id] = item
        tab_idx = id + 1
        if name is None or len(name) == 0:
            self.window.ui.tabs['output'].setTabText(tab_idx, trans('output.tab.notepad') + " " + str(id))
            item.title = ""
            item.initialized = False
        else:
            self.window.ui.tabs['output'].setTabText(tab_idx, name)
            item.title = name
            item.initialized = True
        self.window.core.notepad.update(item)
        if close:
            self.window.ui.dialog['rename'].close()

    def save(self, id: int):
        """
        Save notepad contents

        :param id: notepad id
        """
        item = self.window.core.notepad.get_by_id(id)
        if item is None:
            item = NotepadItem()
            item.id = id
            self.window.core.notepad.items[id] = item

        if id in self.window.ui.notepad:
            prev_content = item.content
            item.content = self.window.ui.notepad[id].toPlainText()
            if prev_content != item.content:  # update only if content changed
                self.window.core.notepad.update(item)
            self.update()

    def save_all(self):
        """Save all notepads contents"""
        items = self.window.core.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for id in range(0, num_notepads + 1):
                if id in self.window.ui.notepad:
                    prev_content = items[id].content
                    items[id].content = self.window.ui.notepad[id].toPlainText()

                    # update only if content changed
                    if prev_content != items[id].content:
                        self.window.core.notepad.update(items[id])
            self.update()

    def setup(self):
        """Setup all notepads"""
        self.load()

    def append_text(self, text: str, id: int):
        """
        Append text to notepad

        :param text: text to append
        :param id: notepad id
        """
        if id not in self.window.ui.notepad:
            return
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.notepad[id].toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.notepad[id].setText(new_text)
        self.save(id)

    def get_num_notepads(self) -> int:
        """
        Get number of notepads

        :return: number of notepads
        :rtype: int
        """
        return self.window.core.config.get('notepad.num') or self.default_num_notepads

    def rename_upd(self, id: int, name: str):
        """
        Rename notepad

        :param id: notepad id
        :param name: new notepad name
        """
        item = self.window.core.notepad.get_by_id(id)
        if item is None:
            item = NotepadItem()
            item.id = id
            self.window.core.notepad.items[id] = item
        item.title = name
        self.window.core.notepad.update(item)
        self.update()

    def update(self):
        """Update notepads UI"""
        pass
