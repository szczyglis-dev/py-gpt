#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 05:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_custom"
        self.name = "Command: Custom Commands"
        self.description = "Provides availability to create and execute custom commands"
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.init_options()

    def init_options(self):
        """Initialize options"""
        keys = {
            "enabled": "bool",
            "name": "text",
            "instruction": "textarea",
            "params": "textarea",
            "cmd": "textarea",
        }
        items = [
            {
                "enabled": True,
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
        self.add_option(
            "cmds",
            type="dict",
            value=items,
            label="Your custom commands",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for item in self.get_option_value("cmds"):
            if not item["enabled"]:
                continue

            cmd_syntax = {
                "cmd": item["name"],
                "instruction": item["instruction"],  # instruction for model
                "params": [],  # parameters
                "enabled": True,  # enabled
            }
            if item["params"].strip() != "":
                cmd_syntax["params"] = self.extract_params(item["params"])

            data['cmd'].append(cmd_syntax)  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            for my_cmd in self.get_option_value("cmds"):
                if not my_cmd["enabled"]:
                    continue
                if my_cmd["name"] == item["cmd"]:
                    is_cmd = True
                    my_commands.append(item)

        if not is_cmd:
            return

        try:
            # worker
            self.worker = Worker()
            self.worker.plugin = self
            self.worker.cmds = my_commands
            self.worker.ctx = ctx

            # signals (base handlers)
            self.worker.signals.finished_more.connect(self.handle_finished_more)
            self.worker.signals.log.connect(self.handle_log)
            self.worker.signals.debug.connect(self.handle_debug)
            self.worker.signals.status.connect(self.handle_status)
            self.worker.signals.error.connect(self.handle_error)

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                self.worker.run()
                return

            # start
            self.window.threadpool.start(self.worker)

        except Exception as e:
            self.error(e)

    def extract_params(self, text: str) -> list:
        """
        Extract params from params string

        :param text: text
        :return: params list
        """
        params = []
        if text is None or text == "":
            return params
        params_list = text.split(",")
        for param in params_list:
            param = param.strip()
            if param == "":
                continue
            params.append({
                "name": param,
                "type": "str",
                "description": param,
            })
        return params

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        if self.is_threaded():
            return
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
