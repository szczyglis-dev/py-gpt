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
            "hour",
            type="bool",
            value=True,
            label="Append time",
            description="If enabled, current time will be appended to system prompt.",
            tooltip="Hour will be appended to system prompt.",
        )
        plugin.add_option(
            "date",
            type="bool",
            value=True,
            label="Append date",
            description="If enabled, current date will be appended to system prompt.",
            tooltip="Date will be appended to system prompt.",
        )

        desc = "Template to append to system prompt.\n" \
               "Placeholder {time} will be replaced with current date and time in real-time. "
        tooltip = "Text to append to system prompt."
        plugin.add_option(
            "tpl",
            type="textarea",
            value="Current time is {time}.",
            label="Template",
            description=desc,
            tooltip=tooltip,
        )
        # commands
        plugin.add_cmd(
            "get_time",
            instruction="get current time and date",
            params=[],
            enabled=True,
            description="Enable: Get current time and date.",
        )