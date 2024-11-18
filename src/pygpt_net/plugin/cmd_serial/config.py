#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 19:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        plugin.add_option(
            "serial_port",
            type="text",
            value="/dev/ttyUSB0",
            label="USB port",
            description="USB port name, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM3",
            min=1,
            max=None,
        )
        plugin.add_option(
            "serial_bps",
            type="int",
            value=9600,
            label="Connection speed (baudrate, bps)",
            description="Port connection speed, in bps, default: 9600",
            min=1,
            max=None,
        )
        plugin.add_option(
            "timeout",
            type="int",
            value=1,
            label="Timeout",
            description="Timeout in seconds, default: 1",
            min=0,
            max=None,
        )
        plugin.add_option(
            "sleep",
            type="int",
            value=2,
            label="Sleep",
            description="Sleep in seconds after connection, default: 2",
            min=0,
            max=None,
        )

        # commands
        plugin.add_cmd(
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
        plugin.add_cmd(
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
        plugin.add_cmd(
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