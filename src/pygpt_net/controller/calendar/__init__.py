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

from typing import Optional

from pygpt_net.core.tabs.tab import Tab

from .note import Note


class Calendar:
    def __init__(self, window=None):
        """
        Calendar controller

        :param window: Window instance
        """
        self.window = window
        self.note = Note(window)
        self.selected_year = None
        self.selected_month = None
        self.selected_day = None

    def setup(self):
        """Setup calendar"""
        self.note.setup()
        self.load()
        self.update()  # update counters and load notes for current month
        self.set_current()  # set to current note at start

    def is_loaded(self) -> bool:
        """
        Check if calendar is loaded

        :return: True if calendar is loaded
        """
        return hasattr(self.window.ui, 'calendar') and hasattr(self.window.ui.calendar, 'select')

    def update(self, all: bool = True):
        """
        Update counters

        :param all: reload all notes
        """
        if not self.is_loaded():
            return
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.on_page_changed(year, month, all=all)  # load notes for current month

    def update_ctx_counters(self):
        """Update context counters only"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.note.refresh_ctx(year, month)

    def set_current(self):
        """Set to current selected date"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay

        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)

        self.selected_year = year
        self.selected_month = month
        self.selected_day = day

    def load(self):
        """Load notes from current year and month from database"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.window.core.calendar.load_by_month(year, month)

    def on_page_changed(
            self,
            year: int,
            month: int,
            all: bool = True
    ):
        """
        On calendar page changed

        :param year: year
        :param month: month
        :param all: reload all notes
        """
        if all:
            self.load()  # reload notes for current year and month
        self.note.refresh_ctx(year, month)
        self.note.refresh_num(year, month)

    def on_day_select(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        On day select

        :param year: year
        :param month: month
        :param day: day
        """
        self.selected_year = year
        self.selected_month = month
        self.selected_day = day
        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)

    def on_ctx_select(
            self,
            year: int,
            month: int,
            day: int
    ):
        """
        On ctx select

        :param year: year
        :param month: month
        :param day: day
        """
        search_string = '@date({:04d}-{:02d}-{:02d})'.format(year, month, day)
        self.window.controller.ctx.append_search_string(search_string)

    def save_all(self):
        """Save all calendar notes"""
        self.window.core.calendar.save_all()

    def is_active(self) -> bool:
        """
        Check if calendar tab is active

        :return: True if calendar tab is active
        """
        return self.window.controller.ui.tabs.get_current_type() == Tab.TAB_TOOL_CALENDAR

    def reload(self):
        """Reload calendar"""
        self.setup()

