#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

import copy
from uuid import uuid4

from pygpt_net.item.builder_layout import BuilderLayoutItem
from pygpt_net.provider.core.agent.json_file import JsonFileProvider

class Custom:
    def __init__(self, window=None):
        """
        Custom agents core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)  # json file provider
        self.agents = {}  # dict of AgentItem
        self.layout = None  # BuilderLayoutItem
        self.loaded = False

    def load(self):
        """Load custom agents from provider"""
        data = self.provider.load()
        if "layout" in data:
            self.layout = data["layout"]
        if "agents" in data:
            self.agents = data["agents"]
        self.loaded = True

    def save(self):
        """Save custom agents to provider"""
        self.provider.save(self.layout, self.agents)

    def update_layout(self, layout: dict):
        """
        Update layout of custom agents

        :param layout: layout dict
        """
        if self.layout is None:
            self.layout = BuilderLayoutItem()
        self.layout.data = layout

    def reset(self):
        """Reset custom agents"""
        self.agents = {}
        self.layout = None
        self.loaded = False
        self.provider.truncate()

    def get_layout(self) -> dict:
        """
        Get layout of custom agents

        :return: layout dict
        """
        if not self.loaded:
            self.load()
        return self.layout

    def get_agents(self) -> dict:
        """
        Get custom agents

        :return: dict of AgentItem
        """
        if not self.loaded:
            self.load()
        return self.agents

    def get_agent(self, agent_id: str):
        """
        Get custom agent by ID

        :param agent_id: agent ID
        :return: AgentItem or None
        """
        if not self.loaded:
            self.load()
        return self.agents.get(agent_id)

    def new_agent(self, name: str):
        """
        Create new custom agent

        :param name: agent name
        """
        if not self.loaded:
            self.load()
        new_id = str(uuid4())
        from pygpt_net.item.agent import AgentItem
        new_agent = AgentItem()
        new_agent.id = new_id
        new_agent.name = name
        self.agents[new_id] = new_agent
        self.save()
        return new_id

    def duplicate_agent(self, agent_id: str, new_name: str):
        """
        Duplicate custom agent

        :param agent_id: agent ID
        :param new_name: new agent name
        """
        if not self.loaded:
            self.load()
        agent = self.agents.get(agent_id)
        if agent:
            new_agent = copy.deepcopy(agent)
            new_agent.id = str(uuid4())
            new_agent.name = new_name
            self.agents[new_agent.id] = new_agent
            self.save()

    def delete_agent(self, agent_id: str):
        """
        Delete custom agent

        :param agent_id: agent ID
        """
        if not self.loaded:
            self.load()
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.save()

    def update_agent_layout(self, agent_id: str, layout: dict):
        """
        Update layout of a specific custom agent

        :param agent_id: agent ID
        :param layout: new layout dict
        """
        if not self.loaded:
            self.load()
        agent = self.agents.get(agent_id)
        if agent:
            agent.layout = layout
            self.save()