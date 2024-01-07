#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

import datetime

from PySide6.QtGui import QColor

from pygpt_net.utils import trans


class Calendar:
    def __init__(self, window=None):
        """
        Calendar controller

        :param window: Window instance
        """
        self.window = window
        self.statuses = {
            0: {'label': 'label.color.default', 'color': QColor(100, 100, 100), 'font': QColor(255, 255, 255)},
            1: {'label': 'label.color.red', 'color': QColor(255, 0, 0), 'font': QColor(255, 255, 255)},
            2: {'label': 'label.color.orange', 'color': QColor(255, 165, 0), 'font': QColor(255, 255, 255)},
            3: {'label': 'label.color.yellow', 'color': QColor(255, 255, 0), 'font': QColor(0, 0, 0)},
            4: {'label': 'label.color.green', 'color': QColor(0, 255, 0), 'font': QColor(0, 0, 0)},
            5: {'label': 'label.color.blue', 'color': QColor(0, 0, 255), 'font': QColor(255, 255, 255)},
            6: {'label': 'label.color.indigo', 'color': QColor(75, 0, 130), 'font': QColor(255, 255, 255)},
            7: {'label': 'label.color.violet', 'color': QColor(238, 130, 238), 'font': QColor(255, 255, 255)},
        }

    def setup(self):
        """Setup calendar"""
        self.load_notes()
        self.update()  # update counters and load notes for current month
        self.update_note_current()  # set to current note at start

    def update_note_current(self):
        """Update note to current selected date"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        self.update_note_content(year, month, day)
        self.update_note_label(year, month, day)

    def load_notes(self):
        """Load notes from current year and month from database"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.window.core.calendar.load_by_month(year, month)

    def update(self, all: bool = True):
        """
        Update calendar counters

        :param all: reload all notes
        """
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.on_page_changed(year, month, all=all)  # load notes for current month

    def date_to_key(self, year: int, month: int, day: int) -> str:
        """
        Convert date to key string in format: YYYY-MM-DD

        :param year: year
        :param month: month
        :param day: day
        :return: key string in format: YYYY-MM-DD
        """
        return datetime.datetime(year, month, day).strftime("%Y-%m-%d")

    def update_note(self):
        """Update note on content change"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        content = self.window.ui.calendar['note'].toPlainText()
        note = self.window.core.calendar.get_by_date(year, month, day)
        if note is None:
            note = self.window.core.calendar.build()
            note.year = year
            note.month = month
            note.day = day
            note.content = content
            self.window.core.calendar.add(note)
        else:
            note.content = content
            self.window.core.calendar.update(note)

        self.update_note_cells(year, month)  # update note cells when note is changed

    def update_ctx_cells(self, year: int, month: int):
        """
        Update calendar ctx cells

        :param year: year
        :param month: month
        """
        counters = self.window.core.ctx.provider.get_ctx_count_by_day(year, month)
        self.window.ui.calendar['select'].update_ctx(counters)

    def update_note_cells(self, year: int, month: int):
        """
        Update calendar ctx cells

        :param year: year
        :param month: month
        """
        counters = self.window.core.calendar.get_notes_existence_by_day(year, month)
        self.window.ui.calendar['select'].update_notes(counters)

    def on_page_changed(self, year: int, month: int, all: bool = True):
        """
        On calendar page changed

        :param year: year
        :param month: month
        :param all: reload all notes
        """
        if all:
            self.load_notes()  # reload notes for current year and month
        self.update_ctx_cells(year, month)
        self.update_note_cells(year, month)

    def on_day_select(self, year: int, month: int, day: int):
        """
        On calendar day select

        :param year: Year
        :param month: Month
        :param day: Day
        """
        self.update_note_content(year, month, day)
        self.update_note_label(year, month, day)

    def on_ctx_select(self, year: int, month: int, day: int):
        """
        On calendar day select

        :param year: Year
        :param month: Month
        :param day: Day
        """
        date_search_string = '@date({:04d}-{:02d}-{:02d})'.format(year, month, day)
        self.window.controller.ctx.append_search_string(date_search_string)

    def update_note_content(self, year: int, month: int, day: int):
        """
        Update note content

        :param year: Year
        :param month: Month
        :param day: Day
        """
        note = self.window.core.calendar.get_by_date(year, month, day)
        if note is None:
            self.window.ui.calendar['note'].setPlainText("")
        else:
            self.window.ui.calendar['note'].setPlainText(note.content)

    def update_note_label(self, year: int, month: int, day: int):
        """
        Update note label

        :param year: year
        :param month: month
        :param day: day
        """
        dt_formatted_suffix = datetime.datetime(year, month, day).strftime("%Y-%m-%d")
        self.window.ui.calendar['note.label'].setText(trans('calendar.note.label') + " (" + dt_formatted_suffix + ")")

    def update_current_note_label(self):
        """Update note label to current selected date"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        self.update_note_label(year, month, day)

    def update_status_label(self, status, year, month, day):
        note = self.window.core.calendar.get_by_date(year, month, day)
        if note is None:
            note = self.window.core.calendar.build()
            note.year = year
            note.month = month
            note.day = day
            note.status = status
            self.window.core.calendar.add(note)
        else:
            note.status = status
            self.window.core.calendar.update(note)

        self.update_note_cells(year, month)  # update note cells when note is changed

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
        self.update_note()

    def save_all(self):
        """Save all calendar notes"""
        self.window.core.calendar.save_all()

