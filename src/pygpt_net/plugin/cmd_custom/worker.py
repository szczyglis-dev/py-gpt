#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 13:00:00                  #
# ================================================== #

import os.path
import subprocess
from datetime import datetime
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
            for my_cmd in self.plugin.get_option_value("cmds"):
                request = {"cmd": item["cmd"]}  # prepare request item for result
                if my_cmd["name"] == item["cmd"]:
                    try:
                        # prepare cmd
                        cmd = my_cmd["cmd"]

                        # append system placeholders
                        cmd = cmd.replace("{_file}", os.path.dirname(os.path.realpath(__file__)))
                        cmd = cmd.replace("{_home}", self.plugin.window.core.config.path)
                        cmd = cmd.replace("{_date}", datetime.now().strftime("%Y-%m-%d"))
                        cmd = cmd.replace("{_time}", datetime.now().strftime("%H:%M:%S"))
                        cmd = cmd.replace("{_datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                        # append custom params to cmd placeholders
                        if 'params' in my_cmd and my_cmd["params"].strip() != "":
                            # append params to cmd placeholders
                            params_list = self.plugin.extract_params(
                                my_cmd["params"],
                            )
                            for param in params_list:
                                if param in item["params"]:
                                    cmd = cmd.replace(
                                        "{" + param + "}",
                                        item["params"][param],
                                    )

                        # check if cmd is not empty
                        if cmd is None or cmd == "":
                            msg = "Command is empty"
                            continue

                        # execute custom cmd
                        msg = "Running custom cmd: {}".format(cmd)
                        self.log(msg)
                        process = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        stdout, stderr = process.communicate()
                        result = None
                        if stdout:
                            result = stdout.decode("utf-8")
                            self.log("STDOUT: {}".format(result))
                        if stderr:
                            result = stderr.decode("utf-8")
                            self.log("STDERR: {}".format(result))
                        if result is None:
                            result = "No result (STDOUT/STDERR empty)"
                            self.log(result)

                        response = {
                            "request": request,
                            "result": result,
                        }

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
