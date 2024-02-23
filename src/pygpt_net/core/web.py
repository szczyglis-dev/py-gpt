#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.24 00:00:00                  #
# ================================================== #

from pygpt_net.provider.web.base import BaseProvider


class Web:
    def __init__(self, window=None):
        """
        Web access core

        :param window: Window instance
        """
        self.window = window
        self.providers = {
            "search_engine": {},
        }

    def is_registered(self, id: str, type: str = "search_engine") -> bool:
        """
        Check if provider is registered

        :param id: provider id
        :param type: provider type
        :return: True if registered
        """
        if type in self.providers:
            return id in self.providers[type]
        return False

    def get_providers(self, type: str = "search_engine") -> dict:
        """
        Get all providers

        :param type: provider type
        :return: providers dict
        """
        if type in self.providers:
            return self.providers[type]
        return {}

    def get_ids(self, type: str = "search_engine") -> list:
        """
        Get all providers ids

        :param type: provider type
        :return: providers ids list
        """
        if type in self.providers:
            return list(self.providers[type].keys())
        return []

    def get(self, id: str, type: str = "search_engine") -> BaseProvider or None:
        """
        Get provider instance

        :param id: provider id
        :param type: provider type
        :return: provider instance
        """
        if self.is_registered(id, type):
            return self.providers[type][id]
        return None

    def register(self, provider: BaseProvider):
        """
        Register provider

        :param provider: provider instance
        """
        id = provider.id
        type = provider.type
        for t in type:
            if t in self.providers:
                self.providers[t][id] = provider
