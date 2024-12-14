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

from typing import Dict

from packaging.version import Version

from pygpt_net.item.calendar_note import CalendarNoteItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "calendar_note"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def create(self, notepad: CalendarNoteItem):
        pass

    def load(self, year, month, day) -> CalendarNoteItem:
        pass

    def load_all(self) -> Dict[str, CalendarNoteItem]:
        pass

    def save(self, notepad: CalendarNoteItem):
        pass

    def save_all(self, items: Dict[str, CalendarNoteItem]):
        pass

    def remove(self, year, month, day):
        pass

    def truncate(self):
        pass

    def get_version(self) -> str:
        pass
