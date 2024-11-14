#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

class Provider:
    def __init__(self, window=None):
        """
        Agent providers

        :param window: Window instance
        """
        self.window = window
        self.agents = {}

    def get_ids(self) -> list:
        """
        Get agent providers ids

        :return: agent providers ids
        """
        return list(self.agents.keys())

    def has(self, id: str) -> bool:
        """
        Check if agent exists

        :param id: agent id
        :return: True if exists
        """
        return id in self.agents

    def get(self, id: str):
        """
        Get agent provider

        :param id: agent id
        :return: agent provider
        """
        return self.agents[id]

    def register(self, id: str, agent):
        """
        Register Agent provider

        :param id: Agent id
        :param agent: Agent provider
        """
        self.agents[id] = agent

    def get_providers(self) -> list:
        """
        Get agent providers list

        :return: list of agent providers
        """
        return self.get_ids()