#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from .worker import Worker


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
        """Initialize options"""
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
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.set_status(full_msg)
        print(full_msg)

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

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            for my_cmd in self.get_option_value("cmds"):
                if my_cmd["name"] == item["cmd"]:
                    is_cmd = True
                    my_commands.append(item)

        if not is_cmd:
            return

        # worker
        worker = Worker()
        worker.plugin = self
        worker.cmds = my_commands
        worker.ctx = ctx

        # signals (base handlers)
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.log.connect(self.handle_log)
        worker.signals.debug.connect(self.handle_debug)
        worker.signals.status.connect(self.handle_status)
        worker.signals.error.connect(self.handle_error)

        # start
        self.window.threadpool.start(worker)
