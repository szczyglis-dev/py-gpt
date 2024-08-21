#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 15:00:00                  #
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
        responses = []
        msg = None
        for item in self.cmds:
            response = None
            try:
                if item["cmd"] == "get_context":
                    response = self.cmd_get_context(item)

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
            for response in responses:
                self.reply(response)

        # update status
        if msg is not None:
            self.status(msg)

    def cmd_get_context(self, item: dict) -> dict:
        """
        Get context for given query

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        question = item["params"]["query"]
        self.status("Please wait... querying: {}...".format(question))
        answer, doc_ids, metas = self.plugin.query(question)  # send question to Llama-index
        response = {
            "request": request,
            "result": answer,
            "doc_ids": doc_ids,
            "metas": metas,
            "context": "ADDITIONAL CONTEXT (response from DB):\n--------------------------------\n" + answer,
        }
        if doc_ids:
            self.ctx.doc_ids = doc_ids  # store doc_ids in context
        return response

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}
