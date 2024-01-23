#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

import datetime

from pygpt_net.item.calendar_note import CalendarNoteItem
from pygpt_net.utils import trans


class Note:
    def __init__(self, window=None):
        """
        Calendar note controller

        :param window: Window instance
        """
        self.window = window

    def update(self):
        """Update on content change"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        content = self.window.ui.calendar['note'].toPlainText()
        note = self.window.core.calendar.get_by_date(year, month, day)

        # update or create note
        if note is None:
            note = self.create(year, month, day)
            note.content = content
            self.window.core.calendar.add(note)
        else:
            note.content = content
            self.window.core.calendar.update(note)

        self.refresh_num(year, month)  # update note cells when note is changed

    def update_content(self, year: int, month: int, day: int):
        """
        Update content

        :param year: year
        :param month: month
        :param day: day
        """
        note = self.window.core.calendar.get_by_date(year, month, day)
        if note is None:
            self.window.ui.calendar['note'].setPlainText("")
        else:
            self.window.ui.calendar['note'].setPlainText(note.content)

    def update_label(self, year: int, month: int, day: int):
        """
        Update label

        :param year: year
        :param month: month
        :param day: day
        """
        suffix = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        self.window.ui.calendar['note.label'].setText(trans('calendar.note.label') + " (" + suffix + ")")

    def update_current(self):
        """Update label to current selected date"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        self.update_label(year, month, day)

    def update_status(self, status: str, year: int, month: int, day: int):
        """
        Update status label

        :param status: status
        :param year: year
        :param month: month
        :param day: day
        """
        note = self.window.core.calendar.get_by_date(year, month, day)
        if note is None:
            note = self.create(year, month, day)
            note.status = status
            self.window.core.calendar.add(note)
        else:
            note.status = status
            self.window.core.calendar.update(note)

        self.refresh_num(year, month)  # update note cells when note is changed

    def refresh_ctx(self, year: int, month: int):
        """
        Update calendar ctx cells

        :param year: year
        :param month: month
        """
        count = self.window.core.ctx.provider.get_ctx_count_by_day(year, month)
        self.window.ui.calendar['select'].update_ctx(count)

    def create(self, year: int, month: int, day: int) -> CalendarNoteItem:
        """
        Create empty note

        :param year: year
        :param month: month
        :param day: day
        :return: note instance
        """
        note = self.window.core.calendar.build()
        note.year = year
        note.month = month
        note.day = day
        return note

    def refresh_num(self, year: int, month: int):
        """
        Update calendar notes cells

        :param year: year
        :param month: month
        """
        count = self.window.core.calendar.get_notes_existence_by_day(year, month)
        self.window.ui.calendar['select'].update_notes(count)

    def append_text(self, text: str):
        """
        Append text to note

        :param text: text to append
        """
        dt = ""  # TODO: add to config append date/time
        # dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ":\n--------------------------\n"
        prev_text = self.window.ui.calendar['note'].toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + dt + text.strip()
        self.window.ui.calendar['note'].setText(new_text)
        self.update()

