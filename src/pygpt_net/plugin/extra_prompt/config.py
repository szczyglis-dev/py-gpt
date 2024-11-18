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
        # extra prompts
        keys = {
            "enabled": "bool",
            "name": "text",
            "prompt": "textarea",
        }
        items = []
        desc = "Prompt that will be appended to every system prompt. " \
               "All active prompts will be appended to the system prompt in the order they are listed here."
        tooltip = desc
        plugin.add_option(
            "prompts",
            type="dict",
            value=items,
            label="Prompts",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )