#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import datetime

from ..item.notepad import NotepadItem


class Notepad:
    def __init__(self, window=None):
        """
        Notepad controller

        :param window: Window instance
        """
        self.window = window
        self.default_num_notepads = 5

    def load(self):
        """
        Load notepad contents
        """
        self.window.app.notepad.load_all()
        items = self.window.app.notepad.get_all()
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
                    self.window.ui.notepad[id].setText(items[id].content)

    def save(self, id=None):
        """
        Save notepad contents

        :param id: notepad id
        """
        item = self.window.app.notepad.get_by_id(id)
        if item is None:
            item = NotepadItem()
            item.id = id
            self.window.app.notepad.items[id] = item

        if id in self.window.ui.notepad:
            prev_content = item.content
            item.content = self.window.ui.notepad[id].toPlainText()
            if prev_content != item.content:  # update only if content changed
                self.window.app.notepad.update(item)
            self.update()

    def save_all(self):
        """
        Save all notepads contents
        """
        items = self.window.app.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for id in range(1, num_notepads + 1):
                if id in self.window.ui.notepad:
                    prev_content = items[id].content
                    items[id].content = self.window.ui.notepad[id].toPlainText()

                    # update only if content changed
                    if prev_content != items[id].content:
                        self.window.app.notepad.update(items[id])
            self.update()

    def setup(self):
        """Setup all notepads"""
        self.load()

    def append_text(self, text, id):
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

    def get_num_notepads(self):
        """
        Get number of notepads

        :return: number of notepads
        :rtype: int
        """
        return self.window.app.config.get('notepad.num') or self.default_num_notepads

    def update(self):
        """Update notepads UI"""
        pass
