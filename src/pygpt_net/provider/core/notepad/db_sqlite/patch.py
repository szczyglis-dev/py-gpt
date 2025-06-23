#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 04:00:00                  #
# ================================================== #

import os
import shutil
import sys
import time

from packaging.version import parse as parse_version, Version

from pygpt_net.item.notepad import NotepadItem


class Patch:
    def __init__(self, window=None, provider=None):
        self.window = window
        self.provider = provider

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        # return
        # if old version is 2.0.59 or older and if json file exists
        path = os.path.join(self.window.core.config.path, 'notepad.json')
        if os.path.exists(path):
            self.provider.truncate()
            self.import_from_json()
            os.rename(path, path + ".old")  # rename notepad.json to notepad.json.old
            return True

    def import_from_json(self) -> bool:
        """
        Import notepads from JSON file

        :return: True if imported
        :rtype: bool
        """
        return True
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
            notepad.uuid = self.provider.create_id()

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
        self.provider.create(notepad)  # create new notepad and get new ID
