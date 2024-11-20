#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    updated = Signal()  # calendar view update signal


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None

    @Slot()
    def run(self):
        responses = []
        msg = None
        for item in self.cmds:
            if self.is_stopped():
                break
            response = None
            try:
                if item["cmd"] == "get_ctx_list_in_date_range":
                    response = self.cmd_get_ctx_list_in_date_range(item)

                elif item["cmd"] == "get_ctx_content_by_id":
                    response = self.cmd_get_ctx_content_by_id(item)

                elif item["cmd"] == "get_day_note":
                    response = self.cmd_get_day_note(item)

                elif item["cmd"] == "add_day_note":
                    response = self.cmd_add_day_note(item)

                elif item["cmd"] == "update_day_note":
                    response = self.cmd_update_day_note(item)

                elif item["cmd"] == "remove_day_note":
                    response = self.cmd_remove_day_note(item)

                elif item["cmd"] == "count_ctx_in_date":
                    response = self.cmd_count_ctx_in_date(item)

                if response:
                    responses.append(response)

            except Exception as e:
                msg = "Error: {}".format(e)
                responses.append(
                    self.make_response(
                        item,
                        self.throw_error(e)
                    )
                )

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

        # update status
        if msg is not None:
            self.status(msg)

    def cmd_get_ctx_list_in_date_range(self, item: dict) -> dict:
        """
        Get context list in date range

        :param item: command item
        :return: response item
        """
        range = self.get_param(item, "range_query", "")
        result = self.plugin.get_list(range)
        return self.make_response(item, result)

    def cmd_get_ctx_content_by_id(self, item: dict) -> dict:
        """
        Get context content by id

        :param item: command item
        :return: response item
        """
        id = int(self.get_param(item, "id", 0))
        prompt = "Summary this conversation"
        if self.has_param(item, "summary_query"):
            prompt = self.get_param(item, "summary_query")
        result = self.plugin.get_summary(id, prompt)
        return self.make_response(item, result)

    def cmd_get_day_note(self, item: dict) -> dict:
        """
        Get day note

        :param item: command item
        :return: response item
        """
        year = int(self.get_param(item, "year", 0))
        month = int(self.get_param(item, "month", 0))
        day = int(self.get_param(item, "day", 0))
        result = self.plugin.get_day_note(year, month, day)
        return self.make_response(item, result)

    def cmd_add_day_note(self, item: dict) -> dict:
        """
        Add day note

        :param item: command item
        :return: response item
        """
        year = int(self.get_param(item, "year", 0))
        month = int(self.get_param(item, "month", 0))
        day = int(self.get_param(item, "day", 0))
        note = self.get_param(item, "note", "")
        self.signals.updated.emit()
        result = self.plugin.add_day_note(year, month, day, note)
        return self.make_response(item, result)

    def cmd_update_day_note(self, item: dict) -> dict:
        """
        Update day note

        :param item: command item
        :return: response item
        """
        year = int(self.get_param(item, "year", 0))
        month = int(self.get_param(item, "month", 0))
        day = int(self.get_param(item, "day", 0))
        note = self.get_param(item, "content", "")
        self.signals.updated.emit()
        result = self.plugin.update_day_note(year, month, day, note)
        return self.make_response(item, result)

    def cmd_remove_day_note(self, item: dict) -> dict:
        """
        Remove day note

        :param item: command item
        :return: response item
        """
        year = int(self.get_param(item, "year", 0))
        month = int(self.get_param(item, "month", 0))
        day = int(self.get_param(item, "day", 0))
        self.signals.updated.emit()
        result = self.plugin.remove_day_note(year, month, day)
        return self.make_response(item, result)

    def cmd_count_ctx_in_date(self, item: dict) -> dict:
        """
        Count context in date

        :param item: command item
        :return: response item
        """
        year = None
        month = None
        day = None
        if self.has_param(item, "year"):
            tmp_year = self.get_param(item, "year", "")
            if tmp_year != "":
                year = int(tmp_year)
        if self.has_param(item, "month"):
            tmp_month = self.get_param(item, "month", "")
            if tmp_month != "":
                month = int(tmp_month)
        if self.has_param(item, "day"):
            tmp_day = self.get_param(item, "day", "")
            if tmp_day != "":
                day = int(tmp_day)
        result = self.plugin.count_ctx_in_date(year, month, day)
        return self.make_response(item, result)
