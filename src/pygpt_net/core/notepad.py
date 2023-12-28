#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 17:00:00                  #
# ================================================== #

import datetime

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.notepad.db_sqlite import DbSqliteProvider


class Notepad:
    def __init__(self, window=None):
        """
        Notepad

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def get_by_id(self, id):
        """
        Get notepad by id

        :param id: notepad id
        :return: notepad instance
        :rtype: NotepadItem
        """
        if id in self.items:
            return self.items[id]
        return None

    def get_all(self):
        """
        Get all notepads

        :return: notepads dict
        :rtype: dict
        """
        return self.items

    def build(self):
        """
        Build notepad

        :param id: notepad id
        :return: NotepadItem instance
        :rtype: NotepadItem
        """
        item = NotepadItem()
        return item

    def add(self, notepad):
        """
        Add notepad

        :param notepad: NotepadItem instance
        :return: True if success
        :rtype: bool
        """
        id = self.provider.create(notepad)
        notepad.id = id
        self.items[id] = notepad
        self.save(id)
        return True

    def update(self, notepad):
        """
        Update and save notepad

        :param notepad: NotepadItem instance
        :return: True if success
        :rtype: bool
        """
        if notepad.id not in self.items:
            return False

        notepad.updated_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.items[notepad.id] = notepad
        self.save(notepad.id)
        return True

    def load(self, id):
        """
        Load notepad by id

        :param id: notepad id
        """
        self.items[id] = self.provider.load(id)

    def load_all(self):
        """Load all notepads"""
        self.items = self.provider.load_all()

    def save(self, id):
        """
        Save notepad by id

        :param id: notepad id
        :return: True if saved, False if not
        :rtype: bool
        """
        if id not in self.items:
            return False

        self.provider.save(self.items[id])
        return False

    def save_all(self):
        """Save all notepads"""
        self.provider.save_all(self.items)
