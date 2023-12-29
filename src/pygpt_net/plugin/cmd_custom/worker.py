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

import os.path
import subprocess
from datetime import datetime
from urllib.request import Request, urlopen
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
            for my_cmd in self.plugin.get_option_value("cmds"):

                # prepare request item for result
                request_item = {"cmd": item["cmd"]}

                if my_cmd["name"] == item["cmd"]:
                    try:
                        # prepare command
                        command = my_cmd["cmd"]

                        # append system placeholders
                        command = command.replace("{_file}", os.path.dirname(os.path.realpath(__file__)))
                        command = command.replace("{_home}", self.plugin.window.core.config.path)
                        command = command.replace("{_date}", datetime.now().strftime("%Y-%m-%d"))
                        command = command.replace("{_time}", datetime.now().strftime("%H:%M:%S"))
                        command = command.replace("{_datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                        # append custom params to command placeholders
                        if 'params' in my_cmd and my_cmd["params"].strip() != "":
                            # append params to command placeholders
                            params_list = self.plugin.extract_params(my_cmd["params"])
                            for param in params_list:
                                if param in item["params"]:
                                    command = command.replace("{" + param + "}", item["params"][param])

                        # check if command is not empty
                        if command is None or command == "":
                            msg = "Command is empty"
                            continue

                        # execute custom command
                        msg = "Running custom command: {}".format(command)
                        self.signals.log.emit(msg)
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)
                        stdout, stderr = process.communicate()
                        result = None
                        if stdout:
                            result = stdout.decode("utf-8")
                            self.signals.log.emit("STDOUT: {}".format(result))
                        if stderr:
                            result = stderr.decode("utf-8")
                            self.signals.log.emit("STDERR: {}".format(result))
                        if result is None:
                            result = "No result (STDOUT/STDERR empty)"
                            self.signals.log.emit(result)
                        response = {"request": request_item, "result": result}
                    except Exception as e:
                        msg = "Error: {}".format(e)
                        response = {"request": request_item, "result": "Error {}".format(e)}
                        self.signals.error.emit(e)
                        self.signals.log.emit(msg)
                    self.signals.finished.emit(self.ctx, response)

        # update status
        if msg is not None:
            self.signals.log.emit(msg)
            self.signals.status.emit(msg)

    def finish(self, ctx, response):
        self.signals.finished.emit(ctx, response)

    def error(self, err):
        self.signals.error.emit(err)

    def status(self, msg):
        self.signals.status.emit(msg)

    def debug(self, msg):
        self.signals.debug.emit(msg)

    def log(self, msg):
        self.signals.log.emit(msg)
