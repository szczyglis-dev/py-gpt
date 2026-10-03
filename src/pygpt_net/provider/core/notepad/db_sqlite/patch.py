#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import os

from packaging.version import Version

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

    def import_notepad(self, notepad: NotepadItem):
        """
        Import notepad from JSON file

        :param notepad: NotepadItem
        """
        notepad.id = None  # reset old ID to allow creating new
        self.provider.create(notepad)  # create new notepad and get new ID
