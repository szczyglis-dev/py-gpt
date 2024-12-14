#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

from typing import List, Dict

from pygpt_net.plugin.base.plugin import BasePlugin


class BaseProvider:
    def __init__(self, plugin=None):
        """
        Web access base provider

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.id = ""  # unique provider id
        self.name = ""  # name to display
        self.type = []  # allowed: search_engine

    def init(self, plugin: BasePlugin):
        """
        Initialize provider

        :param plugin: plugin instance
        """
        self.attach(plugin)
        self.init_options()

    def attach(self, plugin: BasePlugin):
        """
        Attach plugin instance

        :param plugin: plugin instance
        """
        self.plugin = plugin

    def init_options(self):
        """Initialize provider options (for plugin settings)"""
        pass

    def search(
            self,
            query,
            limit: int = 10,
            offset: int = 0
    ) -> List[str]:
        """
        Execute search query and return list of urls

        :param query: search query
        :param limit: limit
        :param offset: offset
        :return: list of urls
        """
        pass

    def is_configured(self, cmds: List[Dict]) -> bool:
        """
        Check if provider is configured

        :param cmds: executed commands list
        :return: True if configured, False otherwise
        """
        pass

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return ""
