#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
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
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            try:
                request = {"cmd": item["cmd"]}  # prepare request item for result

                # code_execute (from existing file)
                if item["cmd"] == "code_execute_file" and self.plugin.has_cmd("code_execute_file"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.code_execute_file_host(
                                self.ctx,
                                item,
                                request,
                            )
                        else:
                            response = self.plugin.runner.code_execute_file_sandbox(
                                self.ctx,
                                item,
                                request,
                            )
                    except Exception as e:
                        response = {
                            "request": request,
                            "result": "Error: {}".format(e),
                        }
                        self.error(e)
                        self.log("Error: {}".format(e))
                    self.response(response)

                # code_execute (generate and execute)
                elif item["cmd"] == "code_execute" and self.plugin.has_cmd("code_execute"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.code_execute_host(
                                self.ctx,
                                item,
                                request,
                            )
                        else:
                            response = self.plugin.runner.code_execute_sandbox(
                                self.ctx,
                                item,
                                request,
                            )
                    except Exception as e:
                        response = {
                            "request": request,
                            "result": "Error: {}".format(e),
                        }
                        self.error(e)
                        self.log("Error: {}".format(e))
                    self.response(response)

                # sys_exec
                elif item["cmd"] == "sys_exec" and self.plugin.has_cmd("sys_exec"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.sys_exec_host(
                                self.ctx,
                                item,
                                request,
                            )
                        else:
                            response = self.plugin.runner.sys_exec_sandbox(
                                self.ctx,
                                item,
                                request,
                            )
                    except Exception as e:
                        response = {
                            "request": request,
                            "result": "Error: {}".format(e),
                        }
                        self.error(e)
                        self.log("Error: {}".format(e))
                    self.response(response)

            except Exception as e:
                response = {
                    "request": item,
                    "result": "Error: {}".format(e),
                }
                self.response(response)
                self.error(e)
                self.log("Error: {}".format(e))

        if msg is not None:
            self.log(str(msg))
            self.status(str(msg))
