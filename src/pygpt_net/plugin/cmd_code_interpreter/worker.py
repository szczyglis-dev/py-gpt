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
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            try:
                # prepare request item for result
                request_item = {"cmd": item["cmd"]}

                # code_execute (from existing file)
                if item["cmd"] == "code_execute_file" and self.plugin.is_cmd_allowed("code_execute_file"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.code_execute_file_host(self.ctx, item, request_item)
                        else:
                            response = self.plugin.runner.code_execute_file_sandbox(self.ctx, item, request_item)
                    except Exception as e:
                        response = {"request": request_item, "result": "Error: {}".format(e)}
                        self.signals.error.emit(e)
                        self.signals.log.emit("Error: {}".format(e))
                    self.signals.finished.emit(self.ctx, response)

                # code_execute (generate and execute)
                elif item["cmd"] == "code_execute" and self.plugin.is_cmd_allowed("code_execute"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.code_execute_host(self.ctx, item, request_item)
                        else:
                            response = self.plugin.runner.code_execute_sandbox(self.ctx, item, request_item)
                    except Exception as e:
                        response = {"request": request_item, "result": "Error: {}".format(e)}
                        self.signals.error.emit(e)
                        self.signals.log.emit("Error: {}".format(e))
                    self.signals.finished.emit(self.ctx, response)

                # sys_exec
                elif item["cmd"] == "sys_exec" and self.plugin.is_cmd_allowed("sys_exec"):
                    try:
                        if not self.plugin.runner.is_sandbox():
                            response = self.plugin.runner.sys_exec_host(self.ctx, item, request_item)
                        else:
                            response = self.plugin.runner.sys_exec_sandbox(self.ctx, item, request_item)
                    except Exception as e:
                        response = {"request": request_item, "result": "Error: {}".format(e)}
                        self.signals.error.emit(e)
                        self.signals.log.emit("Error: {}".format(e))
                    self.signals.finished.emit(self.ctx, response)
            except Exception as e:
                response = {"request": item, "result": "Error: {}".format(e)}
                self.signals.finished.emit(self.ctx, response)
                self.signals.error.emit(e)
                self.signals.log.emit("Error: {}".format(e))

        if msg is not None:
            self.signals.log.emit(msg)
            self.signals.status.emit(msg)
