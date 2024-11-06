#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

import datetime

from PySide6.QtGui import QTextCursor

from pygpt_net.item.calendar_note import CalendarNoteItem
from pygpt_net.utils import trans


class Note:
    def __init__(self, window=None):
        """
        Calendar note controller

        :param window: Window instance
        """
        self.window = window
        self.counters_all = True

    def setup(self):
        """Setup calendar notes"""
        self.counters_all = self.window.core.config.get("ctx.counters.all", True)

    def update(self):
        """Update on content change"""
        year = self.window.controller.calendar.selected_year
        month = self.window.controller.calendar.selected_month
        day = self.window.controller.calendar.selected_day

        if year is None or month is None or day is None:
            return

        content = self.window.ui.calendar['note'].toPlainText()
        note = self.window.core.calendar.get_by_date(year, month, day)

        # update or create note
        if note is None:
            if content.strip() != "":
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
            self.window.ui.calendar['note'].on_update()
        else:
            self.window.ui.calendar['note'].setPlainText(note.content)
            self.window.ui.calendar['note'].on_update()

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

    def get_counts_around_month(self, year: int, month: int) -> dict:
        """
        Get counts around month

        :param year: year
        :param month: month
        :return: combined counters
        """
        current_month_start = datetime.datetime(year, month, 1)
        last_month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)

        if month == 12:
            next_month_start = datetime.datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime.datetime(year, month + 1, 1)

        current = self.get_ctx_counters(
            year,
            month,
        )
        last = self.get_ctx_counters(
            last_month_start.year,
            last_month_start.month,
        )
        next = self.get_ctx_counters(
            next_month_start.year,
            next_month_start.month,
        )
        return {**last, **current, **next}  # combine counters

    def get_labels_counts_around_month(self, year: int, month: int) -> dict:
        """
        Get counts around month

        :param year: year
        :param month: month
        :return: combined counters
        """
        current_month_start = datetime.datetime(year, month, 1)
        last_month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)

        if month == 12:
            next_month_start = datetime.datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime.datetime(year, month + 1, 1)

        current = self.get_ctx_labels_counters(
            year,
            month,
        )
        last = self.get_ctx_labels_counters(
            last_month_start.year,
            last_month_start.month,
        )
        next = self.get_ctx_labels_counters(
            next_month_start.year,
            next_month_start.month,
        )
        return {**last, **current, **next}  # combine counters

    def get_ctx_counters(self, year: int, month: int) -> dict:
        """
        Get ctx counters

        :param year: year
        :param month: month
        :return: ctx counters
        """
        # default values (no filters)
        search_string = None
        search_content = False
        filters = None

        # + filters
        if not self.counters_all:
            search_string = self.window.core.ctx.get_search_string()
            search_content = self.window.core.ctx.is_search_content()
            filters = self.window.core.ctx.get_parsed_filters()

        return self.window.core.ctx.provider.get_ctx_count_by_day(
            year=year,
            month=month,
            day=None,
            search_string=search_string,
            filters=filters,
            search_content=search_content,
        )

    def get_ctx_labels_counters(self, year: int, month: int) -> dict:
        """
        Get ctx labels counters

        :param year: year
        :param month: month
        :return: ctx counters
        """
        # default values (no filters)
        search_string = None
        search_content = False
        filters = None

        # + filters
        if not self.counters_all:
            search_string = self.window.core.ctx.get_search_string()
            search_content = self.window.core.ctx.is_search_content()
            filters = self.window.core.ctx.get_parsed_filters()

        return self.window.core.ctx.provider.get_ctx_labels_count_by_day(
            year=year,
            month=month,
            day=None,
            search_string=search_string,
            filters=filters,
            search_content=search_content,
        )

    def refresh_ctx(self, year: int, month: int):
        """
        Update calendar ctx cells

        :param year: year
        :param month: month
        """
        count = self.get_counts_around_month(year, month)
        labels = self.get_labels_counts_around_month(year, month)
        self.window.ui.calendar['select'].update_ctx(count, labels)

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

    def get_notes_existence_around_month(self, year: int, month: int) -> dict:
        """
        Get notes existence around month

        :param year: year
        :param month: month
        :return: combined notes existence
        """
        current_month_start = datetime.datetime(year, month, 1)
        last_month_start = (current_month_start - datetime.timedelta(days=1)).replace(day=1)
        if month == 12:
            next_month_start = datetime.datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime.datetime(year, month + 1, 1)

        current = self.window.core.calendar.get_notes_existence_by_day(
            year,
            month,
        )
        last = self.window.core.calendar.get_notes_existence_by_day(
            last_month_start.year,
            last_month_start.month,
        )
        next = self.window.core.calendar.get_notes_existence_by_day(
            next_month_start.year,
            next_month_start.month,
        )
        return {**last, **current, **next}  # combine notes existence

    def refresh_num(self, year: int, month: int):
        """
        Update calendar notes cells

        :param year: year
        :param month: month
        """
        count = self.get_notes_existence_around_month(year, month)
        self.window.ui.calendar['select'].update_notes(count)

    def toggle_counters_all(self, state: bool):
        """
        Toggle counters all

        :param state: state
        """
        self.counters_all = state
        self.window.core.config.set("ctx.counters.all", state)
        self.window.core.config.save()
        self.window.controller.calendar.update_ctx_counters()

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

        # move cursor to end
        cursor = self.window.ui.calendar['note'].textCursor()
        cursor.movePosition(QTextCursor.End)
        self.window.ui.calendar['note'].setTextCursor(cursor)

    def clear_note(self):
        """Clear note"""
        self.window.ui.calendar['note'].clear()
        self.update()
        self.window.ui.calendar['note'].on_update()

    def get_note_text(self) -> str:
        """
        Get notepad text

        :return: notepad text
        """
        return self.window.ui.calendar['note'].toPlainText()
