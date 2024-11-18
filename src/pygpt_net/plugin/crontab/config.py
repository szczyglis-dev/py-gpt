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
        keys = {
            "enabled": "bool",
            "crontab": "text",
            "prompt": "textarea",
            "preset": {
                "type": "combo",
                "use": "presets",
                "keys": [],
            },
        }
        items = [
            {
                "enabled": False,
                "crontab": "30 9 * * *",
                "prompt": "Hi! This prompt should be sent at 9:30 every day. What time is it?",
                "preset": "_",
            },
        ]
        desc = "Add your cron-style tasks here. They will be executed automatically at the times you specify in " \
               "the cron-based job format. If you are unfamiliar with Cron, consider visiting the Cron Guru " \
               "page for assistance."
        tooltip = "Check out the tutorials about Cron or visit the Crontab Guru for help on how to use Cron syntax."
        plugin.add_option(
            "crontab",
            type="dict",
            value=items,
            label="Your tasks",
            description=desc,
            tooltip=tooltip,
            keys=keys,
            urls={
                "Crontab Guru": "https://crontab.guru",
            },
        )
        plugin.add_option(
            "new_ctx",
            type="bool",
            value=True,
            label="Create a new context on job run",
            description="If enabled, then a new context will be created on every run of the job",
        )
        plugin.add_option(
            "show_notify",
            type="bool",
            value=True,
            label="Show notification on job run",
            description="If enabled, then a tray notification will be shown on every run of the job",
        )