#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QRunnable, Slot, QObject, Signal


class WorkerSignals(QObject):
    finished = Signal(object, object)  # ctx, response
    log = Signal(object)
    debug = Signal(object)
    status = Signal(object)
    error = Signal(object)


class Worker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.websearch = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        # connect signals
        self.websearch.signals = self.signals

        msg = None
        for item in self.cmds:

            # prepare request item for result
            request_item = {"cmd": item["cmd"]}

            try:
                # cmd: web_search
                if item["cmd"] == "web_search":
                    page = 1
                    if "page" in item["params"]:
                        page = int(item["params"]["page"])
                    summarize_prompt = None
                    if "summarize_prompt" in item["params"]:
                        summarize_prompt = item["params"]["summarize_prompt"]

                    # search for query
                    result, total_found, current, url = self.websearch.make_query(item["params"]["query"],
                                                                                  page, summarize_prompt)
                    msg = "Web search finished: '{}'".format(item["params"]["query"])
                    data = {
                        'content': result,
                        'url': url,
                        'page': current,
                        'total_found': total_found,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    response = {"request": request_item, "result": data}
                    self.signals.finished.emit(self.ctx, response)

                # cmd: web_url_open
                elif item["cmd"] == "web_url_open":
                    summarize_prompt = None
                    if "summarize_prompt" in item["params"]:
                        summarize_prompt = item["params"]["summarize_prompt"]
                    url = item["params"]["url"]
                    msg = "Opening Web URL: '{}'".format(item["params"]["url"])

                    # open url
                    result, url = self.websearch.open_url(url, summarize_prompt)
                    data = {
                        'content': result,
                        'url': url,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    response = {"request": request_item, "result": data}
                    self.signals.finished.emit(self.ctx, response)

            except Exception as e:
                response = {"request": item, "result": "Error: {}".format(e)}
                self.signals.finished.emit(self.ctx, response)
                self.signals.error.emit(e)
                self.signals.log("Error: {}".format(e))

        if msg is not None:
            self.signals.log.emit(msg)
            self.signals.status.emit(msg)



