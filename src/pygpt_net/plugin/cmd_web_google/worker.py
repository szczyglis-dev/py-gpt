#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot
from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
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
        self.websearch.signals = self.signals  # connect signals

        msg = None
        for item in self.cmds:
            request = {"cmd": item["cmd"]}  # prepare request item for result

            try:
                # cmd: web_search
                if item["cmd"] == "web_search":
                    page = 1
                    if "page" in item["params"]:
                        page = int(item["params"]["page"])
                    prompt = None
                    if "summarize_prompt" in item["params"]:
                        prompt = item["params"]["summarize_prompt"]

                    # search for query
                    result, total_found, current, url = self.websearch.make_query(item["params"]["query"],
                                                                                  page, prompt)
                    msg = "Web search finished: '{}'".format(item["params"]["query"])
                    data = {
                        'content': result,
                        'url': url,
                        'page': current,
                        'total_found': total_found,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response({"request": request, "result": data})

                # cmd: web_url_open
                elif item["cmd"] == "web_url_open":
                    prompt = None
                    if "summarize_prompt" in item["params"]:
                        prompt = item["params"]["summarize_prompt"]
                    url = item["params"]["url"]
                    msg = "Opening Web URL: '{}'".format(item["params"]["url"])

                    # open url
                    result, url = self.websearch.open_url(url, prompt)
                    data = {
                        'content': result,
                        'url': url,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response({"request": request, "result": data})

            except Exception as e:
                self.response({"request": item, "result": "Error: {}".format(e)})
                self.error(e)
                self.log("Error: {}".format(e))

        if msg is not None:
            self.log(msg)
            self.status(msg)
