#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 05:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    updated = Signal()  # calendar view update signal


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        responses = []
        msg = None
        for item in self.cmds:
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
                responses.append({
                    "request": {
                        "cmd": item["cmd"],
                    },
                    "result": "Error {}".format(e),
                })
                self.error(e)
                self.log(msg)

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
        request = self.prepare_request(item)
        range = item["params"]["range_query"]
        response = {
            "request": request,
            "result":  self.plugin.get_list(range)
        }
        return response

    def cmd_get_ctx_content_by_id(self, item: dict) -> dict:
        """
        Get context content by id

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        id = int(item["params"]["id"])
        prompt = "Summary this conversation"
        if "summary_query" in item["params"]:
            prompt = item["params"]["summary_query"]
        response = {
            "request": request,
            "result": self.plugin.get_summary(id, prompt),
        }
        return response

    def cmd_get_day_note(self, item: dict) -> dict:
        """
        Get day note

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        year = int(item["params"]["year"])
        month = int(item["params"]["month"])
        day = int(item["params"]["day"])
        response = {
            "request": request,
            "result": self.plugin.get_day_note(year, month, day),
        }
        return response

    def cmd_add_day_note(self, item: dict) -> dict:
        """
        Add day note

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        year = int(item["params"]["year"])
        month = int(item["params"]["month"])
        day = int(item["params"]["day"])
        note = item["params"]["note"]
        response = {
            "request": request,
            "result": self.plugin.add_day_note(year, month, day, note),
        }
        self.signals.updated.emit()
        return response

    def cmd_update_day_note(self, item: dict) -> dict:
        """
        Update day note

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        year = int(item["params"]["year"])
        month = int(item["params"]["month"])
        day = int(item["params"]["day"])
        note = item["params"]["content"]
        response = {
            "request": request,
            "result": self.plugin.update_day_note(year, month, day, note),
        }
        self.signals.updated.emit()
        return response

    def cmd_remove_day_note(self, item: dict) -> dict:
        """
        Remove day note

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        year = int(item["params"]["year"])
        month = int(item["params"]["month"])
        day = int(item["params"]["day"])
        response = {
            "request": request,
            "result": self.plugin.remove_day_note(year, month, day),
        }
        self.signals.updated.emit()
        return response

    def cmd_count_ctx_in_date(self, item: dict) -> dict:
        """
        Count context in date

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        year = None
        month = None
        day = None
        if "year" in item["params"] and item["params"]["year"] != "":
            year = int(item["params"]["year"])
        if "month" in item["params"] and item["params"]["month"] != "":
            month = int(item["params"]["month"])
        if "day" in item["params"] and item["params"]["day"] != "":
            day = int(item["params"]["day"])
        response = {
            "request": request,
            "result": self.plugin.count_ctx_in_date(year, month, day),
        }
        return response

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}
