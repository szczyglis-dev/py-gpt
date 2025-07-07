#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import datetime
import uuid
from typing import Optional, Dict

from packaging.version import Version

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.core.notepad.db_sqlite import DbSqliteProvider
from pygpt_net.utils import trans


class Notepad:
    def __init__(self, window=None):
        """
        Notepad core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.items = {}
        self.locked = False

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def reset(self):
        """Reset provider data"""
        self.items = {}

    def get_by_id(self, idx: int) -> Optional[NotepadItem]:
        """
        Get notepad by idx

        :param idx: notepad idx
        :return: notepad instance
        """
        if idx in self.items:
            return self.items[idx]
        return None

    def get_all(self) -> Dict[int, NotepadItem]:
        """
        Get all notepads

        :return: notepads dict
        """
        return self.items

    def build(self) -> NotepadItem:
        """
        Build notepad

        :param idx: notepad idx
        :return: NotepadItem instance
        """
        item = NotepadItem()
        return item

    def add(self, notepad: NotepadItem) -> bool:
        """
        Add notepad

        :param notepad: NotepadItem instance
        :return: True if success
        """
        idx = self.provider.create(notepad)
        notepad.id = idx
        self.items[idx] = notepad
        self.save(idx)
        return True

    def update(self, notepad: NotepadItem) -> bool:
        """
        Update and save notepad

        :param notepad: NotepadItem instance
        :return: True if success
        """
        if notepad.idx not in self.items:
            return False

        notepad.updated_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.items[notepad.idx] = notepad
        self.save(notepad.idx)
        return True

    def load(self, idx: int):
        """
        Load notepad by idx

        :param idx: notepad idx
        """
        self.items[idx] = self.provider.load(idx)

    def load_all(self):
        """Load all notepads"""
        self.items = self.provider.load_all()

    def save(self, idx: int) -> bool:
        """
        Save notepad by idx

        :param idx: notepad idx
        :return: True if saved, False if not
        :rtype: bool
        """
        if idx not in self.items:
            return False

        self.provider.save(self.items[idx])
        return False

    def save_all(self):
        """Save all notepads"""
        self.provider.save_all(self.items)

    def import_from_db(self) -> Optional[Dict[int, dict]]:
        """
        Import notepad tabs from database

        :return: dict with tabs
        """
        self.load_all()
        items = self.get_all()
        if len(items) == 0:
            return
        data = {}
        for idx in items:
            item = items[idx]
            tab = {
                "uuid": uuid.uuid4(),
                "pid": 0,
                "idx": item.idx,
                "type": Tab.TAB_NOTEPAD,
                "data_id": item.idx,
                "title": item.title,
            }
            if tab['title'] == "":
                tab['title'] = trans('output.tab.notepad')
            data[item.idx] = tab
        return data
