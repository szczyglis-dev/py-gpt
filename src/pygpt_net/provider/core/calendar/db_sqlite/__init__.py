#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.07 23:00:00                  #
# ================================================== #

import uuid

from packaging.version import Version

from pygpt_net.item.calendar_note import CalendarNoteItem
from pygpt_net.provider.core.calendar.base import BaseProvider
from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "calendar_note"

    def attach(self, window):
        """
        Attach window instance to provider

        :param window: window instance
        """
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

    def create(self, note: CalendarNoteItem) -> int:
        """
        Create new and return its ID

        :param note: CalendarNoteItem
        :return: note ID
        """
        if note.id is None or note.id == "":
            note.id = self.storage.insert(note)
        return note.id

    def load_all(self) -> dict:
        """
        Load notes from DB

        :return: dict with notes
        """
        return self.storage.get_all()

    def load_by_month(self, year: int, month: int) -> dict:
        """
        Load notes from DB

        :return: notes
        """
        return self.storage.get_by_month(year, month)

    def load(self, year: int, month: int, day: int) -> CalendarNoteItem:
        """
        Load note from DB

        :param year: year
        :param month: month
        :param day: day
        :return: CalendarNoteItem object
        """
        return self.storage.get_by_date(year, month, day)

    def get_notes_existence_by_day(self, year, month) -> dict:
        """
        Get notes existence by day

        :param year: year
        :param month: month
        :return: notes existence by day
        """
        return self.storage.get_notes_existence_by_day(year, month)

    def save(self, note: CalendarNoteItem):
        """
        Save note to DB

        :param note: CalendarNoteItem
        """
        try:
            self.storage.save(note)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving note: {}".format(str(e)))

    def save_all(self, items: dict):
        """
        Save all notes to DB

        :param items: dict of CalendarNoteItem objects
        """
        try:
            for dt in items:
                note = items[dt]
                self.storage.save(note)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving note: {}".format(str(e)))

    def remove(self, year: int, month: int, day: int):
        """
        Remove note from DB

        :param year: year
        :param month: month
        :param day: day
        """
        self.storage.delete_by_date(year, month, day)

    def truncate(self) -> bool:
        """
        Truncate all notes

        :return: True if truncated
        :rtype: bool
        """
        return self.storage.truncate_all()

