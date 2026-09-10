#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 14:00:00                  #
# ================================================== #

import os.path
import shlex
import subprocess

from datetime import datetime
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


_PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))
_IS_WINDOWS = os.name == "nt"


def _quote_param(value: str) -> str:
    """
    Quote a single parameter value for the host shell.

    POSIX shells (Linux/macOS) use single-quote style quoting via shlex.
    Windows cmd.exe does not understand POSIX quoting, so use the
    Windows command-line quoting (subprocess.list2cmdline) instead.
    """
    if _IS_WINDOWS:
        return subprocess.list2cmdline([value])
    return shlex.quote(value)


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
        try:
            responses = []
            msg = None
            configured_cmds = self.plugin.get_option_value("cmds")
            for item in self.cmds:
                if self.is_stopped():
                    break
                for my_cmd in configured_cmds:
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

            if len(responses) > 0:
                self.reply_more(responses) # send response

            if msg is not None:
                self.status(msg)  # update status

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

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
            # Replace placeholders with actual values. A no-op replace on a
            # token that is absent returns the string unchanged, so the extra
            # ``if token in cmd`` guards are not needed and we avoid rescanning.
            now = datetime.now()
            cmd = cmd.replace("{_file}", _PLUGIN_DIR)
            cmd = cmd.replace("{_home}", self.plugin.window.core.config.path)
            cmd = cmd.replace("{_date}", now.strftime("%Y-%m-%d"))
            cmd = cmd.replace("{_time}", now.strftime("%H:%M:%S"))
            cmd = cmd.replace("{_datetime}", now.strftime("%Y-%m-%d %H:%M:%S"))
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
                    # Sanitize parameter value to prevent shell injection
                    cmd = cmd.replace(
                        "{%s}" % param["name"],
                        _quote_param(str(item["params"][param["name"]])),
                    )

        # execute on host (Security command rules apply)
        self.security_command(cmd, sandbox=False)
        msg = "Running custom cmd: {}".format(cmd)
        self.log(msg)
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        result_parts = []
        if stdout:
            result_parts.append(stdout.decode("utf-8", errors="replace"))
        if stderr:
            result_parts.append(stderr.decode("utf-8", errors="replace"))
        if result_parts:
            result = "\n".join(result_parts)
            for part in result_parts:
                self.log(part)
        else:
            result = "No result (STDOUT/STDERR empty)"
            self.log(result)

        return self.make_response(item, result)
