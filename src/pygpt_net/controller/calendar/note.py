#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

import datetime
from typing import Dict

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

    def _adjacent_months(self, year: int, month: int):
        if month == 1:
            py, pm = year - 1, 12
        else:
            py, pm = year, month - 1
        if month == 12:
            ny, nm = year + 1, 1
        else:
            ny, nm = year, month + 1
        return (py, pm), (ny, nm)

    def update(self):
        """Update on content change"""
        ctrl_cal = self.window.controller.calendar
        year = ctrl_cal.selected_year
        month = ctrl_cal.selected_month
        day = ctrl_cal.selected_day

        if year is None or month is None or day is None:
            return

        ui_note = self.window.ui.calendar['note']
        content = ui_note.toPlainText()
        cal = self.window.core.calendar
        note = cal.get_by_date(year, month, day)

        changed = False
        if note is None:
            if content.strip():
                note = self.create(year, month, day)
                note.content = content
                cal.add(note)
                changed = True
        else:
            if note.content != content:
                note.content = content
                cal.update(note)
                changed = True

        if changed:
            self.refresh_num(year, month)

    def update_content(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        Update content

        :param year: year
        :param month: month
        :param day: day
        """
        ui_note = self.window.ui.calendar['note']
        note = self.window.core.calendar.get_by_date(year, month, day)
        new_text = "" if note is None else note.content
        if ui_note.toPlainText() != new_text:
            ui_note.setPlainText(new_text)
        ui_note.on_update()

    def update_label(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        Update label

        :param year: year
        :param month: month
        :param day: day
        """
        suffix = f"{year:04d}-{month:02d}-{day:02d}"
        self.window.ui.calendar['note.label'].setText(f"{trans('calendar.note.label')} ({suffix})")

    def update_current(self):
        """Update label to current selected date"""
        select = self.window.ui.calendar['select']
        self.update_label(select.currentYear, select.currentMonth, select.currentDay)

    def update_status(
            self,
            status: str,
            year: int,
            month: int,
            day: int
    ):
        """
        Update status label

        :param status: status
        :param year: year
        :param month: month
        :param day: day
        """
        cal = self.window.core.calendar
        note = cal.get_by_date(year, month, day)
        changed = False
        if note is None:
            note = self.create(year, month, day)
            note.status = status
            cal.add(note)
            changed = True
        else:
            if note.status != status:
                note.status = status
                cal.update(note)
                changed = True

        if changed:
            self.refresh_num(year, month)

    def get_counts_around_month(
            self,
            year: int,
            month: int
    ) -> Dict[str, int]:
        """
        Get counts around month

        :param year: year
        :param month: month
        :return: combined counters
        """
        (ly, lm), (ny, nm) = self._adjacent_months(year, month)
        result: Dict[str, int] = {}
        result.update(self.get_ctx_counters(ly, lm))
        result.update(self.get_ctx_counters(year, month))
        result.update(self.get_ctx_counters(ny, nm))
        return result

    def get_labels_counts_around_month(
            self,
            year: int,
            month: int
    ) -> Dict[str, Dict[int, int]]:
        """
        Get counts around month

        :param year: year
        :param month: month
        :return: combined counters
        """
        (ly, lm), (ny, nm) = self._adjacent_months(year, month)
        result: Dict[str, Dict[int, int]] = {}
        result.update(self.get_ctx_labels_counters(ly, lm))
        result.update(self.get_ctx_labels_counters(year, month))
        result.update(self.get_ctx_labels_counters(ny, nm))
        return result

    def get_ctx_counters(
            self,
            year: int,
            month: int
    ) -> Dict[str, int]:
        """
        Get ctx counters

        :param year: year
        :param month: month
        :return: ctx counters
        """
        ctx = self.window.core.ctx
        if self.counters_all:
            search_string = None
            search_content = False
            filters = None
        else:
            search_string = ctx.get_search_string()
            search_content = ctx.is_search_content()
            filters = ctx.get_parsed_filters()

        return ctx.provider.get_ctx_count_by_day(
            year=year,
            month=month,
            day=None,
            search_string=search_string,
            filters=filters,
            search_content=search_content,
        )

    def get_ctx_labels_counters(
            self,
            year: int,
            month: int
    ) -> Dict[str, Dict[int, int]]:
        """
        Get ctx labels counters

        :param year: year
        :param month: month
        :return: ctx counters
        """
        ctx = self.window.core.ctx
        if self.counters_all:
            search_string = None
            search_content = False
            filters = None
        else:
            search_string = ctx.get_search_string()
            search_content = ctx.is_search_content()
            filters = ctx.get_parsed_filters()

        return ctx.provider.get_ctx_labels_count_by_day(
            year=year,
            month=month,
            day=None,
            search_string=search_string,
            filters=filters,
            search_content=search_content,
        )

    def refresh_ctx(
            self,
            year: int,
            month: int
    ):
        """
        Update calendar ctx cells

        :param year: year
        :param month: month
        """
        count = self.get_counts_around_month(year, month)
        labels = self.get_labels_counts_around_month(year, month)
        self.window.ui.calendar['select'].update_ctx(count, labels)

    def create(
            self,
            year: int,
            month: int,
            day: int
    ) -> CalendarNoteItem:
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

    def get_notes_existence_around_month(
            self,
            year: int,
            month: int
    ) -> Dict[str, Dict[int, int]]:
        """
        Get notes existence around month

        :param year: year
        :param month: month
        :return: combined notes existence
        """
        (ly, lm), (ny, nm) = self._adjacent_months(year, month)
        cal = self.window.core.calendar
        result: Dict[str, Dict[int, int]] = {}
        result.update(cal.get_notes_existence_by_day(ly, lm))
        result.update(cal.get_notes_existence_by_day(year, month))
        result.update(cal.get_notes_existence_by_day(ny, nm))
        return result

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
        if self.counters_all == state:
            return
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
        editor = self.window.ui.calendar['note']
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        if not editor.document().isEmpty():
            cursor.insertText("\n\n")
        cursor.insertText(dt + text.strip())
        editor.setTextCursor(cursor)
        self.update()

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