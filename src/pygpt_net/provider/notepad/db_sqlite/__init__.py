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

import os
import sys
import time
import shutil
import uuid

from packaging.version import Version

from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.notepad.base import BaseProvider
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
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
        # return
        # if old version is 2.0.59 or older and if json file exists
        path = os.path.join(self.window.core.config.path, 'notepad.json')
        if os.path.exists(path):
            self.truncate()
            self.import_from_json()
            os.rename(path, path + ".old")  # rename notepad.json to notepad.json.old
            return True

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, notepad: NotepadItem) -> str:
        """
        Create new and return its ID

        :param notepad: NotepadItem
        :return: notepad ID
        """
        if notepad.id is None or notepad.id == "":
            notepad.id = self.storage.insert(notepad)
        return notepad.id

    def load_all(self) -> dict:
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

    def save_all(self, items: dict):
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

    def import_from_json(self) -> bool:
        """
        Import notepads from JSON file

        :return: True if imported
        :rtype: bool
        """
        # use json provider to load old notepads
        provider = self.window.core.notepad.providers['json_file']
        provider.attach(self.window)

        print("[DB] Migrating into database storage...")
        print("[DB] Importing notepads from JSON files... this may take a while. Please wait...")
        i = 0
        notepads = provider.load_all()
        cols, _ = shutil.get_terminal_size()
        c = len(notepads)
        ts = int(time.time())
        for id in notepads:
            notepad = notepads[id]
            notepad.created = ts
            notepad.updated = ts
            notepad.idx = int(id)
            notepad.uuid = self.create_id()

            line = "[DB] Importing notepad %s/%s" % (i + 1, c)
            print(f"{line:<{cols}}", end='\r')
            sys.stdout.flush()

            self.import_notepad(notepad)
            i += 1

        print()  # new line
        if i > 0:
            print("[DB][DONE] Imported %s notepads." % i)
            return True

    def import_notepad(self, notepad: NotepadItem):
        """
        Import notepad from JSON file

        :param notepad: NotepadItem
        """
        notepad.id = None  # reset old ID to allow creating new
        self.create(notepad)  # create new notepad and get new ID
