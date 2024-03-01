#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.01 02:00:00                  #
# ================================================== #

import json

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
                    result, total_found, current, url = self.websearch.make_query(
                        item["params"]["query"],
                        page,
                        prompt,
                    )
                    msg = "Web search finished: '{}'".format(item["params"]["query"])
                    data = {
                        'content': result,
                        'url': url,
                        'page': current,
                        'total_found': total_found,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response(
                        {
                            "request": request,
                            "result": data,
                        }
                    )

                # cmd: web_url_open
                elif item["cmd"] == "web_url_open":
                    prompt = None
                    if "summarize_prompt" in item["params"]:
                        prompt = item["params"]["summarize_prompt"]
                    url = item["params"]["url"]
                    msg = "Opening Web URL: '{}'".format(item["params"]["url"])

                    # open url
                    result, url = self.websearch.open_url(
                        url,
                        prompt,
                    )
                    data = {
                        'content': result,
                        'url': url,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response(
                        {
                            "request": request,
                            "result": data,
                        }
                    )

                # cmd: web_url_raw
                elif item["cmd"] == "web_url_raw":
                    url = item["params"]["url"]
                    msg = "Opening Web URL: '{}'".format(item["params"]["url"])

                    # open url (raw)
                    result, url = self.websearch.open_url_raw(
                        url,
                    )
                    data = {
                        'content': result,
                        'url': url,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response(
                        {
                            "request": request,
                            "result": data,
                        }
                    )

                # cmd: web_urls
                elif item["cmd"] == "web_urls":
                    page = 1
                    num = 10
                    if "page" in item["params"]:
                        page = int(item["params"]["page"])
                    if "num_links" in item["params"]:
                        num = int(item["params"]["num_links"])
                    if num < 1:
                        num = 1
                    if num > 10:
                        num = 10
                    offset = 1
                    if page > 1:
                        offset = (page - 1) * num + 1

                    # search for URLs
                    urls = self.websearch.google_search(
                        item["params"]["query"],
                        num,
                        offset,
                    )
                    msg = "Web search finished: '{}'".format(item["params"]["query"])
                    data = {
                        'urls': json.dumps(urls),
                        'page': page,
                        'num': num,
                        'offset': offset,
                    }
                    if urls:
                        for url in urls:
                            self.ctx.urls.append(url)

                    self.response(
                        {
                            "request": request,
                            "result": data,
                        }
                    )

                # cmd: web_index
                elif item["cmd"] == "web_index":
                    type = "webpage"  # default
                    args = {}

                    if "type" in item["params"]:
                        type = item["params"]["type"]
                    if "args" in item["params"]:
                        args = item["params"]["args"]

                    url = type
                    if "url" in item["params"]:
                        url = item["params"]["url"]  # from default param
                    if "url" in args:
                        url = args["url"]  # override from args

                    msg = "Indexing URL: '{}'".format(url)
                    idx_name = self.plugin.get_option_value("idx")

                    # show status
                    self.status("Please wait... indexing: {}...".format(url))

                    # index URL via Llama-index
                    num, errors = self.plugin.window.core.idx.index_urls(
                        idx=idx_name,
                        urls=[url],
                        type=type,
                        extra_args=args,
                    )
                    data = {
                        'num_indexed': num,
                        'index': idx_name,
                        'errors': errors,
                        'url': url,
                    }
                    if url:
                        self.ctx.urls.append(url)

                    self.response(
                        {
                            "request": request,
                            "result": data,
                        }
                    )

            except Exception as e:
                self.response(
                    {
                        "request": item,
                        "result": "Error: {}".format(e),
                    }
                )
                self.error(e)
                self.log("Error: {}".format(e))

        if msg is not None:
            self.log(msg)
            self.status(msg)
