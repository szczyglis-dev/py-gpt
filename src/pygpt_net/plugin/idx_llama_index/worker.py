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

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            response = {}
            request = {"cmd": item["cmd"]}  # prepare request item for result
            try:
                if item["cmd"] == "get_context":
                    question = item["params"]["query"]
                    self.status("Please wait... querying: {}...".format(question))
                    answer, doc_ids, metas = self.plugin.query(question)  # send question to Llama-index
                    response = {
                        "request": request,
                        "result": answer,
                        "doc_ids": doc_ids,
                        "metas": metas,
                        "context": "ADDITIONAL CONTEXT:\n--------------------------------\n" + answer,
                    }
                    self.ctx.results.append(response)
                    self.ctx.reply = True
                    # store doc_ids in context
                    if doc_ids:
                        self.ctx.doc_ids = doc_ids
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
