#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.13 15:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    updated = Signal()


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
        msg = None
        response = {}
        for item in self.cmds:
            request = {"cmd": item["cmd"]}  # prepare request item for result
            try:
                if item["cmd"] == "get_ctx_list_in_date_range":
                    range = item["params"]["range_query"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.plugin.get_list(range)
                    response = {
                        "request": request,
                        "result": data,
                    }

                elif item["cmd"] == "get_ctx_content_by_id":
                    id = int(item["params"]["id"])
                    request = {
                        "cmd": item["cmd"],
                    }
                    prompt = item["params"]["summary_query"]
                    data = self.plugin.get_summary(id, prompt)
                    response = {
                        "request": request,
                        "result": data,
                    }

                elif item["cmd"] == "get_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.plugin.get_day_note(year, month, day)
                    response = {
                        "request": request,
                        "result": data,
                    }

                elif item["cmd"] == "add_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    note = item["params"]["note"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    print("Adding note: " + note, year, month, day)
                    data = self.plugin.add_day_note(year, month, day, note)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    self.signals.updated.emit()

                elif item["cmd"] == "update_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    note = item["params"]["content"]
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.plugin.update_day_note(year, month, day, note)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    self.signals.updated.emit()

                elif item["cmd"] == "remove_day_note":
                    year = int(item["params"]["year"])
                    month = int(item["params"]["month"])
                    day = int(item["params"]["day"])
                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.plugin.remove_day_note(year, month, day)
                    response = {
                        "request": request,
                        "result": data,
                    }
                    self.signals.updated.emit()

                elif item["cmd"] == "count_ctx_in_date":
                    year = None
                    month = None
                    day = None
                    if "year" in item["params"] and item["params"]["year"] != "":
                        year = int(item["params"]["year"])
                    if "month" in item["params"] and item["params"]["month"] != "":
                        month = int(item["params"]["month"])
                    if "day" in item["params"] and item["params"]["day"] != "":
                        day = int(item["params"]["day"])

                    request = {
                        "cmd": item["cmd"],
                    }
                    data = self.plugin.count_ctx_in_date(year, month, day)
                    response = {
                        "request": request,
                        "result": data,
                    }
            except Exception as e:
                msg = "Error: {}".format(e)
                response = {
                    "request": request,
                    "result": "Error {}".format(e),
                }
                self.error(e)
                self.log(msg)

            self.response(response)

        # update status
        if msg is not None:
            self.status(msg)
