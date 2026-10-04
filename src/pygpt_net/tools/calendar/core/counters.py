#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Conversation and day-note counters for one calendar frontend."""
from typing import Dict

class Counters:
    def __init__(self, session):
        self.session = session
        self.window = session.window

    @property
    def counters_all(self):
        return bool(self.window.core.config.get('ctx.counters.all', True))

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
        self.session.widgets['select'].update_ctx(count, labels)


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
        cal = self.session.tool.storage
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
        self.session.widgets['select'].update_notes(count)


    def toggle_counters_all(self, state: bool):
        """
        Toggle counters all

        :param state: state
        """
        if self.counters_all == state:
            return
        self.window.core.config.set("ctx.counters.all", state)
        self.window.core.config.save()
        self.session.tool.refresh()


