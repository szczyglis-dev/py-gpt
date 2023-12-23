#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 04:00:00                  #
# ================================================== #
import os.path
import subprocess
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_custom"
        self.name = "Command: Custom Commands"
        self.description = "Provides availability to create and execute custom commands"
        self.window = None
        self.order = 100
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        keys = {
            "name": "text",
            "instruction": "text",
            "params": "text",
            "cmd": "text",
        }
        value = [
            {
                "name": "example_cmd",
                "instruction": "execute tutorial test command by replacing 'hello' and 'world' params with some funny "
                               "words",
                "params": "hello, world",
                "cmd": 'echo "Response from {hello} and {world} at {_time}"',
            },
        ]
        desc = "Add your custom commands here, use {placeholders} to receive params, you can also use predefined " \
               "placeholders: {_time}, {_date}, {_datetime}, {_file}, {_home) "
        tooltip = "See the documentation for more details about examples, usage and list of predefined placeholders"
        self.add_option("cmds", "dict", value,
                        "Your custom commands", desc, tooltip, keys=keys)

    def setup(self):
        """
        Return available config options

        :return: config options
        :rtype: dict
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'cmd.syntax':
            self.cmd_syntax(data)
        elif name == 'cmd.execute':
            self.cmd(ctx, data['commands'])

    def log(self, msg):
        """
        Log message to console

        :param msg: message to log
        """
        self.debug('[CMD] ' + str(msg))
        print('[CMD] ' + str(msg))

    def cmd_syntax(self, data):
        """
        Event: On cmd syntax prepare

        :param data: event data dict
        """
        for item in self.get_option_value("cmds"):
            cmd = {
                "cmd": item["name"],
                "instruction": item["instruction"],
                "params": [],
            }
            if item["params"].strip() != "":
                params = self.extract_params(item["params"])
                if len(params) > 0:
                    cmd["params"] = params

            data['syntax'].append(cmd)

    def extract_params(self, text):
        """
        Extract params from params string

        :param text: text
        :return: params list
        :rtype: list
        """
        params = []
        if text is None or text == "":
            return params
        params_list = text.split(",")
        for param in params_list:
            param = param.strip()
            if param == "":
                continue
            params.append(param)
        return params

    def cmd(self, ctx, cmds):
        """
        Event: On command

        :param ctx: ContextItem
        :param cmds: commands dict
        """
        msg = None
        for item in cmds:
            for my_cmd in self.get_option_value("cmds"):

                # prepare request item for result
                request_item = {"cmd": item["cmd"]}

                if my_cmd["name"] == item["cmd"]:
                    try:
                        # prepare command
                        command = my_cmd["cmd"]

                        # append system placeholders
                        command = command.replace("{_file}", os.path.dirname(os.path.realpath(__file__)))
                        command = command.replace("{_home}", self.window.config.path)
                        command = command.replace("{_date}", datetime.now().strftime("%Y-%m-%d"))
                        command = command.replace("{_time}", datetime.now().strftime("%H:%M:%S"))
                        command = command.replace("{_datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                        # append custom params to command placeholders
                        if 'params' in my_cmd and my_cmd["params"].strip() != "":
                            # append params to command placeholders
                            params_list = self.extract_params(my_cmd["params"])
                            for param in params_list:
                                if param in item["params"]:
                                    command = command.replace("{" + param + "}", item["params"][param])

                        # check if command is not empty
                        if command is None or command == "":
                            msg = "Command is empty"
                            continue

                        # execute custom command
                        msg = "Running custom command: {}".format(command)
                        self.log(msg)
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)
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
                        ctx.results.append({"request": request_item, "result": result})
                        ctx.reply = True  # send result message
                    except Exception as e:
                        msg = "Error: {}".format(e)
                        ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                        ctx.reply = True
                        self.window.app.error.log(e)
                        self.log(msg)

        # update status
        if msg is not None:
            self.window.set_status(msg)
