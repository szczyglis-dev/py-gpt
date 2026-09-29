#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 22:30:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin
from .prompts import get_inline_plugin_prompts


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
            "iterations",
            type="int",
            value=3,
            label="Iterations",
            description="How many iterations to run? 0 = infinite.\n"
                        "WARNING: setting this to 0 can cause a lot of requests and heavy tokens usage!",
            min=0,
            max=100,
            multiplier=1,
            step=1,
            slider=True,
        )
        # prompts list
        keys = {
            "enabled": "bool",
            "name": "text",
            "prompt": "textarea",
        }
        items = get_inline_plugin_prompts()
        desc = "Prompt used to instruct how to handle autonomous mode. You can create as many prompts as you want. " \
               "The first active prompt on the list will be used to handle autonomous mode."
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
        plugin.add_option(
            "auto_stop",
            type="bool",
            value=True,
            label="Auto-stop after goal is reached",
            description="If enabled, plugin will stop after goal is reached.",
        )
        plugin.add_option(
            "always_continue",
            type="bool",
            value=False,
            label="Always continue",
            description="If enabled, plugin will always continue to the next iteration, even if the goal is reached.",
        )
        plugin.add_option(
            "dynamic_continue",
            type="bool",
            value=True,
            label="Dynamic continuous prompt",
            description="If enabled, after every completed pass a hidden call to the selected model acts as a judge, reviews the configured tail of the current Human/Assistant run, and generates the instruction for the next pass.",
        )
        plugin.add_option(
            "dynamic_continue_messages",
            type="int",
            value=3,
            label="Responses to judge",
            description="Number of the most recent Autonomous assistant responses included in each judge request. The original user input is always included. Set to 0 to include all responses produced since that user input.",
            min=0,
            max=100,
            multiplier=1,
            step=1,
            slider=True,
        )
        plugin.add_option(
            "reverse_roles",
            type="bool",
            value=True,
            label="Reverse roles between iterations",
            description="If enabled, roles will be reversed between iterations.",
        )