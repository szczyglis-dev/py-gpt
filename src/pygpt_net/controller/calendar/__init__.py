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

class Calendar:
    def __init__(self, window=None):
        """
        Calendar controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup calendar"""
        self.update()

    def update(self):
        """Update calendar counters"""
        year = self.window.ui.calendar['select'].currentYear
        month = self.window.ui.calendar['select'].currentMonth
        self.on_page_changed(year, month)

    def update_ctx_cells(self, year: int, month: int):
        """
        Update calendar context cells

        :param year: Year
        :param month: Month
        """
        ctx_count = self.window.core.ctx.provider.get_ctx_count_by_day(year, month)
        self.window.ui.calendar['select'].update_ctx(ctx_count)

    def on_page_changed(self, year: int, month: int):
        """
        On calendar page changed

        :param year: Year
        :param month: Month
        """
        self.update_ctx_cells(year, month)

    def on_day_select(self, year: int, month: int, day: int):
        """
        On calendar day select

        :param year: Year
        :param month: Month
        :param day: Day
        """
        date_search_string = '@date({:04d}-{:02d}-{:02d})'.format(year, month, day)
        self.window.controller.ctx.append_search_string(date_search_string)

