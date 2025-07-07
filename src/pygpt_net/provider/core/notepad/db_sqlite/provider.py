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

import uuid
from typing import Dict

from packaging.version import Version

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.core.notepad.base import BaseProvider
from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "notepad"

    def attach(self, window):
        self.window = window
        self.storage.attach(window)

    def patch(self, version: Version) -> bool:
        """
        Patch versions

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, notepad: NotepadItem) -> int:
        """
        Create new and return its ID

        :param notepad: NotepadItem
        :return: notepad ID
        """
        if notepad.id is None or notepad.id == "":
            notepad.id = self.storage.insert(notepad)
        return notepad.id

    def load_all(self) -> Dict[int, NotepadItem]:
        """
        Load notepads from DB

        :return: notepads
        """
        return self.storage.get_all()

    def load(self, idx: int) -> NotepadItem:
        """
        Load notepad from DB

        :param idx: notepad IDx
        :return: notepad
        """
        return self.storage.get_by_idx(idx)

    def save(self, notepad: NotepadItem):
        """
        Save notepad to DB

        :param notepad: NotepadItem
        """
        try:
            self.storage.save(notepad)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def save_all(self, items: Dict[int, NotepadItem]):
        """
        Save all notepads to DB

        :param items: dict of NotepadItem objects
        """
        try:
            for idx in items:
                notepad = items[idx]
                self.storage.save(notepad)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def truncate(self) -> bool:
        """
        Truncate all notepads

        :return: True if truncated
        :rtype: bool
        """
        return self.storage.truncate_all()


