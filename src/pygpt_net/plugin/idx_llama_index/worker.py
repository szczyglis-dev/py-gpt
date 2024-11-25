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

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


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
            if self.is_stopped():
                break
            response = None
            try:
                if item["cmd"] == "get_context":
                    response = self.cmd_get_context(item)

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

    def cmd_get_context(self, item: dict) -> dict:
        """
        Get context for given query

        :param item: command item
        :return: response item
        """
        question = self.get_param(item, "query")
        self.status("Please wait... querying: {}...".format(question))
        # at first, try to get from retrieval
        response = self.plugin.get_from_retrieval(question)
        if response is not None and response != "":
            self.log("Found using retrieval...")
            context = "ADDITIONAL CONTEXT (response from DB):\n--------------------------------\n" + response
            extra = {
                "context": context,
            }
            return self.make_response(item, response, extra=extra)

        content, doc_ids, metas = self.plugin.query(question)  # send question to Llama-index
        result = content
        context = "ADDITIONAL CONTEXT (response from DB):\n--------------------------------\n" + content
        if doc_ids:
            self.ctx.doc_ids = doc_ids  # store doc_ids in context

        extra = {
            "doc_ids": doc_ids,
            "metas": metas,
            "context": context,
        }
        return self.make_response(item, result, extra=extra)
