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
            "name": "text",
            "instruction": "textarea",
            "get_params": "textarea",
            "post_params": "textarea",
            "post_json": "textarea",
            "headers": "textarea",
            "type": {
                "type": "combo",
                "keys": [
                    {"GET": "GET"},
                    {"POST": "POST"},
                    {"POST_JSON": "POST_JSON"},
                ],
            },
            "endpoint": "textarea",
        }
        items = [
            {
                "enabled": True,
                "name": "search_wiki",
                "instruction": "send API call to Wikipedia to search pages by query",
                "get_params": "query, limit",
                "post_params": "",
                "post_json": "",
                "headers": "",
                "type": "GET",
                "endpoint": 'https://en.wikipedia.org/w/api.php?action=opensearch&limit={limit}&format=json&search={query}',
            },
        ]
        desc = "Add your custom API calls here"
        tooltip = "See the documentation for more details about examples, usage and list of predefined placeholders"
        plugin.add_option(
            "cmds",
            type="dict",
            value=items,
            label="Your custom API calls",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )
        plugin.add_option(
            "disable_ssl",
            type="bool",
            value=False,
            label="Disable SSL verify",
            description="Disables SSL verification when making calls to API",
            tooltip="Disable SSL verify",
        )
        plugin.add_option(
            "timeout",
            type="int",
            value=5,
            label="Timeout",
            description="Connection timeout (seconds)",
            tooltip="Connection timeout (seconds)",
        )
        plugin.add_option(
            "user_agent",
            type="text",
            value="Mozilla/5.0",
            label="User agent",
            description="User agent to use when making requests, default: Mozilla/5.0",
            tooltip="User agent to use when making requests",
        )