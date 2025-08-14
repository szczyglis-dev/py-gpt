#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
# ================================================== #

from typing import List, Dict

from pygpt_net.provider.agents.base import BaseAgent


class Provider:
    def __init__(self, window=None):
        """
        Agent providers

        :param window: Window instance
        """
        self.window = window
        self.agents = {}

    def get_ids(self) -> List[str]:
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

    def get(self, id: str) -> BaseAgent:
        """
        Get agent provider

        :param id: agent id
        :return: agent provider
        """
        if id in self.agents:
            return self.agents[id]

    def all(self) -> Dict[str, BaseAgent]:
        """
        Get all agents

        :return: dict of agent providers
        """
        return self.agents

    def register(self, id: str, agent):
        """
        Register Agent provider

        :param id: Agent id
        :param agent: Agent provider
        """
        self.agents[id] = agent

    def get_providers(self) -> List[str]:
        """
        Get agent providers list

        :return: list of agent providers
        """
        return self.get_ids()

    def get_choices(self, type: str = None) -> List[dict]:
        """
        Get agent providers choices

        :param type: filter by agent type (optional)
        :return: list of agent providers choices
        """
        choices = []
        for id in self.get_ids():
            agent = self.get(id)
            if type is not None:
                if agent.type != type:
                    continue
            choices.append({id: agent.name})

        # sort by name
        choices.sort(key=lambda x: list(x.values())[0].lower())
        return choices
