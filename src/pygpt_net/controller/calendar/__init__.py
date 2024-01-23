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

from PySide6.QtGui import QColor

from .note import Note


class Calendar:
    def __init__(self, window=None):
        """
        Calendar controller

        :param window: Window instance
        """
        self.window = window
        self.note = Note(window)
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
        self.load()
        self.update()  # update counters and load notes for current month
        self.set_current()  # set to current note at start

    def update(self, all: bool = True):
        """
        Update counters

        :param all: reload all notes
        """
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.on_page_changed(year, month, all=all)  # load notes for current month

    def set_current(self):
        """Set to current selected date"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        day = self.window.ui.calendar['select'].currentDay
        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)

    def load(self):
        """Load notes from current year and month from database"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.window.core.calendar.load_by_month(year, month)

    def on_page_changed(self, year: int, month: int, all: bool = True):
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

    def on_day_select(self, year: int, month: int, day: int):
        """
        On day select

        :param year: year
        :param month: month
        :param day: day
        """
        self.note.update_content(year, month, day)
        self.note.update_label(year, month, day)

    def on_ctx_select(self, year: int, month: int, day: int):
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

