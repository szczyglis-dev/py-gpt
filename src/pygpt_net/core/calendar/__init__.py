#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import datetime
from typing import Optional, Dict

from packaging.version import Version

from pygpt_net.item.calendar_note import CalendarNoteItem
from pygpt_net.provider.core.calendar.db_sqlite import DbSqliteProvider


class Calendar:
    def __init__(self, window=None):
        """
        Calendar core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """
        Patch provider data

        :param app_version: app version
        """
        self.provider.patch(app_version)

    def get_by_date(
            self,
            year: int,
            month: int,
            day: int
    ) -> Optional[CalendarNoteItem]:
        """
        Get note by date

        :param year: year
        :param month: month
        :param day: day
        :return: notepad instance
        """
        # convert to format: YYYY-MM-DD:
        dt_key = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        if dt_key in self.items:
            return self.items[dt_key]
        return None

    def get_all(self) -> Dict[str, CalendarNoteItem]:
        """
        Get all notes

        :return: notepads dict
        """
        return self.items

    def build(self) -> CalendarNoteItem:
        """
        Build note

        :return: CalendarNoteItem instance
        """
        item = CalendarNoteItem()
        return item

    def add(self, note: CalendarNoteItem) -> bool:
        """
        Add note

        :param note: CalendarNoteItem instance
        :return: True if success
        """
        self.provider.create(note)
        dt_key = datetime.datetime(note.year, note.month, note.day).strftime("%Y-%m-%d")
        self.items[dt_key] = note
        self.save(note.year, note.month, note.day)
        return True

    def update(self, note: CalendarNoteItem) -> bool:
        """
        Update and save note

        :param note: CalendarNoteItem instance
        :return: True if success
        """
        # convert to format: YYYY-MM-DD:
        dt_key = datetime.datetime(note.year, note.month, note.day).strftime("%Y-%m-%d")
        if dt_key not in self.items:
            return False
        note.updated_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.items[dt_key] = note
        self.save(note.year, note.month, note.day)
        return True

    def load(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        Load note by idx

        :param year: year
        :param month: month
        :param day: day
        """
        # convert to format: YYYY-MM-DD:
        dt_key = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        self.items[dt_key] = self.provider.load(year, month, day)

    def load_note(
            self,
            year: int,
            month: int,
            day: int
    ) -> str:
        """
        Load note by idx

        :param year: year
        :param month: month
        :param day: day
        :return: note content
        """
        note = self.provider.load(year, month, day)
        if note is not None:
            return str(note.content)
        return ""

    def append_to_note(
            self,
            year: int,
            month: int,
            day: int,
            text: str
    ) -> bool:
        """
        Append to note

        :param year: year
        :param month: month
        :param day: day
        :param text: text
        :return: True if success
        """
        current = self.provider.load(year, month, day)
        if current is None:
            current = self.build()
        if current.content is not None and current.content != "":
            current.content = current.content + "\n"
        if current.content is None:
            current.content = ""
        current.year = year
        current.month = month
        current.day = day
        current.content += text
        self.provider.save(current)
        self.load(year, month, day)
        return True

    def update_note(
            self,
            year: int,
            month: int,
            day: int,
            text: str
    ) -> bool:
        """
        Append to note

        :param year: year
        :param month: month
        :param day: day
        :param text: text
        :return: True if success
        """
        current = self.provider.load(year, month, day)
        if current is None:
            current = self.build()
            current.year = year
            current.month = month
            current.day = day
        current.content = text
        self.provider.save(current)
        self.load(year, month, day)
        return True

    def remove_note(
            self,
            year: int,
            month: int,
            day: int
    ) -> bool:
        """
        Remove note by date

        :param year: year
        :param month: month
        :param day: day
        :return: True if removed
        """
        self.provider.remove(year, month, day)
        # convert to format: YYYY-MM-DD:
        dt_key = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        if dt_key in self.items:
            del self.items[dt_key]
        return True

    def load_all(self):
        """Load all notes"""
        self.items = self.provider.load_all()

    def load_by_month(self, year: int, month: int):
        """
        Load notes by month

        :param year: year
        :param month: month
        """
        self.items = self.provider.load_by_month(year, month)

    def get_notes_existence_by_day(
            self,
            year: int,
            month: int
    ) -> Dict[str, Dict[int, int]]:
        """
        Get notes existence by day

        :param year: year
        :param month: month
        :return: dict
        """
        return self.provider.get_notes_existence_by_day(year, month)

    def save(
            self,
            year: int,
            month: int,
            day: int
    ) -> bool:
        """
        Save note by date

        :param year: year
        :param month: month
        :param day: day
        :return: True if saved, False if not
        """
        # convert to format: YYYY-MM-DD:
        dt_key = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        if dt_key not in self.items:
            return False

        self.provider.save(self.items[dt_key])
        return False

    def save_all(self):
        """Save all notes"""
        self.provider.save_all(self.items)
