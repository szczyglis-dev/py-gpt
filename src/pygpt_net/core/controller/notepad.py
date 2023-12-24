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
                for i in range(1, num_notepads + 1):
                    item = NotepadItem()
                    item.id = i
                    items[i] = item

        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                id = 'notepad' + str(i)
                if i not in items:
                    item = NotepadItem()
                    item.id = i
                    items[i] = item
                if id in self.window.ui.nodes:
                    self.window.ui.nodes['notepad' + str(i)].setText(items[i].content)

    def save(self, id=None):
        """
        Save notepad contents
        """
        item = self.window.app.notepad.get_by_id(id)
        if item is None:
            item = NotepadItem()
            item.id = id
            self.window.app.notepad.items[id] = item

        node_id = 'notepad' + str(id)
        if id in self.window.ui.nodes:
            prev_content = item.content
            item.content = self.window.ui.nodes[node_id].toPlainText()
            if prev_content != item.content:  # update only if content changed
                self.window.app.notepad.update(item)
            self.update()

    def save_all(self):
        """
        Save notepad contents
        """
        items = self.window.app.notepad.get_all()
        num_notepads = self.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                id = 'notepad' + str(i)
                if id in self.window.ui.nodes:
                    prev_content = items[i].content
                    items[i].content = self.window.ui.nodes[id].toPlainText()

                    # update only if content changed
                    if prev_content != items[i].content:
                        self.window.app.notepad.update(items[i])
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
        node_id = 'notepad' + str(id)
        if node_id not in self.window.ui.nodes:
            return
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.nodes['notepad' + str(id)].toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.nodes['notepad' + str(id)].setText(new_text)
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
