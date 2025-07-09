#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.09 21:00:00                  #
# ================================================== #

import os.path
import subprocess

from datetime import datetime
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
            for my_cmd in self.plugin.get_option_value("cmds"):
                if self.is_stopped():
                    break
                if my_cmd["name"] == item["cmd"]:
                    try:
                        response = self.handle_cmd(my_cmd, item)
                        if response is False:
                            msg = "Command is empty"
                            continue
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
        # prepare cmd
        cmd = command["cmd"]

        # check if cmd is not empty
        if cmd is None or cmd == "":
            return False
        
        try:
            # replace placeholders with actual values
            if "{_file}" in cmd:
                cmd = cmd.replace("{_file}", os.path.dirname(os.path.realpath(__file__)))
            if "{_home}" in cmd:
                cmd = cmd.replace("{_home}", self.plugin.window.core.config.path)
            if "{_date}" in cmd:
                cmd = cmd.replace("{_date}", datetime.now().strftime("%Y-%m-%d"))
            if "{_time}" in cmd:
                cmd = cmd.replace("{_time}", datetime.now().strftime("%H:%M:%S"))
            if "{_datetime}" in cmd:
                cmd = cmd.replace("{_datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            pass

        # append params to placeholders
        if 'params' in command and command["params"].strip() != "":
            # append params to cmd placeholders
            params_list = self.plugin.extract_params(
                command["params"],
            ) # returns list of dicts
            for param in params_list:
                if param["name"] in item["params"]:
                    cmd = cmd.replace(
                        "{" + param["name"] + "}",
                        str(item["params"][param["name"]]),
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

        return self.make_response(item, result)
