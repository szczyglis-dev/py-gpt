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
            "cmd_prefix",
            type="textarea",
            value="Execute voice command",
            label="Magic prefix for voice commands",
            description="Optional magic prefix required for voice commands, e.g. 'OK PyGPT', 'Execute voice command', etc.",
            urls={
                "Help": "https://pygpt.readthedocs.io/en/latest/accessibility.html",
            },
        )