#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.19 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    output = Signal(object, str)
    html_output = Signal(object)
    ipython_output = Signal(object)
    build_finished = Signal()
    clear = Signal()


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
        for item in self.cmds:
            if self.is_stopped():
                break
            try:
                response = None
                if (item["cmd"] in self.plugin.allowed_cmds
                        and (self.plugin.has_cmd(item["cmd"]) or 'force' in item)):

                    if item["cmd"] == "sys_exec":
                        response = self.cmd_sys_exec(item)

                    if response:
                        responses.append(response)

            except Exception as e:
                responses.append(
                    self.make_response(
                        item,
                        self.throw_error(e)
                    )
                )

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

    def cmd_sys_exec(self, item: dict) -> dict:
        """
        Execute system command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                result = self.plugin.runner.sys_exec_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.sys_exec_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def prepare_extra(self, item: dict, result: dict) -> dict:
        """
        Prepare extra data for response

        :param item: command item
        :param result: response data
        :return: extra data
        """
        cmd = item["cmd"]
        extra = {
            'plugin': "cmd_system",
            'cmd': cmd,
            'code': {}
        }
        lang = "python"
        if cmd in ["sys_exec"]:
            lang = "bash"
        if "params" in item and "code" in item["params"]:
            extra["code"]["input"] = {}
            extra["code"]["input"]["lang"] = lang
            extra["code"]["input"]["content"] = str(item["params"]["code"])
        if "result" in result:
            extra["code"]["output"] = {}
            extra["code"]["output"]["lang"] = lang
            extra["code"]["output"]["content"] = str(result["result"])
        if "context" in result:
            extra["context"] = str(result["context"])
        return extra


