#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 12:00:00                  #
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
        responses = []
        msg = None
        for item in self.cmds:
            for my_cmd in self.plugin.get_option_value("cmds"):
                if my_cmd["name"] == item["cmd"]:
                    try:
                        response = self.handle_cmd(my_cmd, item)
                        if response is False:
                            msg = "Command is empty"
                            continue
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

    def handle_cmd(self, command: dict, item: dict) -> dict or bool:
        """
        Handle custom command

        :param command: command configuration
        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)

        # prepare cmd
        cmd = command["cmd"]

        # check if cmd is not empty
        if cmd is None or cmd == "":
            return False
        
        try:
            cmd = cmd.format(
                _file=os.path.dirname(os.path.realpath(__file__)),
                _home=self.plugin.window.core.config.path,
                _date=datetime.now().strftime("%Y-%m-%d"),
                _time=datetime.now().strftime("%H:%M:%S"),
                _datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            pass

        # append params to placeholders
        if 'params' in command and command["params"].strip() != "":
            # append params to cmd placeholders
            params_list = self.plugin.extract_params(
                command["params"],
            )
            for param in params_list:
                if param in item["params"]:
                    cmd = cmd.replace(
                        "{" + param + "}",
                        str(item["params"][param]),
                    )

        # execute
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

        # prepare response
        response = {
            "request": request,
            "result": result,
        }
        return response

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}
