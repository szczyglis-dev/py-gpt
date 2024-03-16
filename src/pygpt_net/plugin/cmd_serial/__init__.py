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

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem

from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_serial"
        self.name = "Command: Serial port / USB"
        self.description = "Provides commands for reading and sending data to USB ports"
        self.order = 100
        self.allowed_cmds = [
            "serial_send",
            "serial_send_bytes",
            "serial_read",
        ]
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "serial_port",
            type="text",
            value="/dev/ttyUSB0",
            label="USB port",
            description="USB port name, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM3",
            min=1,
            max=None,
        )
        self.add_option(
            "serial_bps",
            type="int",
            value=9600,
            label="Connection speed (baudrate, bps)",
            description="Port connection speed, in bps, default: 9600",
            min=1,
            max=None,
        )
        self.add_option(
            "timeout",
            type="int",
            value=1,
            label="Timeout",
            description="Timeout in seconds, default: 1",
            min=0,
            max=None,
        )
        self.add_option(
            "sleep",
            type="int",
            value=2,
            label="Sleep",
            description="Sleep in seconds after connection, default: 2",
            min=0,
            max=None,
        )

        # commands
        self.add_cmd(
            "serial_send",
            instruction="send text command to USB port",
            params=[
                {
                    "name": "command",
                    "type": "str",
                    "description": "command",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Send text commands to USB port",
        )
        self.add_cmd(
            "serial_send_bytes",
            instruction="send raw bytes to USB port",
            params=[
                {
                    "name": "bytes",
                    "type": "int",
                    "description": "bytes",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Send raw bytes to USB port",
        )
        self.add_cmd(
            "serial_read",
            instruction="read data from serial port in seconds duration",
            params=[
                {
                    "name": "duration",
                    "type": "int",
                    "description": "duration",
                    "required": True,
                },
            ],
            enabled=True,
            description="Enable: Read data from USB port",
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
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        try:
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

            # check if async allowed
            if not self.window.core.dispatcher.async_allowed(ctx):
                worker.run()
                return

            # start
            self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def log(self, msg: str):
        """
        Log message to console

        :param msg: message to log
        """
        full_msg = '[CMD] ' + str(msg)
        self.debug(full_msg)
        self.window.ui.status(full_msg)
        if self.is_log():
            print(full_msg)
