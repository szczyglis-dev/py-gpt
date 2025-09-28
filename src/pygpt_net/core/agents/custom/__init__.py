#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.25 14:00:00                  #
# ================================================== #

import copy
from uuid import uuid4

from pygpt_net.core.types import MODEL_DEFAULT
from pygpt_net.item.agent import AgentItem
from pygpt_net.item.builder_layout import BuilderLayoutItem
from pygpt_net.provider.core.agent.json_file import JsonFileProvider
from pygpt_net.utils import trans


class Custom:

    CUSTOM_AGENT_SUFFIX = " *"  # suffix for custom agents in lists

    def __init__(self, window=None):
        """
        Custom agents core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)  # JSON file provider
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

    def reload(self):
        """Reload custom agents from provider"""
        self.loaded = False
        self.load()

    def save(self):
        """Save custom agents to provider"""
        self.provider.save(self.layout, self.agents)

    def is_custom(self, agent_id: str) -> bool:
        """
        Check if agent is custom

        :param agent_id: agent ID
        :return: True if custom
        """
        if not self.loaded:
            self.load()
        return agent_id in self.agents

    def update_layout(self, layout: dict):
        """
        Update current layout of custom agents editor

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

    def get_choices(self) -> list:
        """
        Get custom agents choices

        :return: list of dict with 'id' and 'name'
        """
        if not self.loaded:
            self.load()
        return [{agent.id: f"{agent.name}{self.CUSTOM_AGENT_SUFFIX}"} for agent in self.agents.values()]

    def get_agent(self, agent_id: str):
        """
        Get custom agent by ID

        :param agent_id: agent ID
        :return: AgentItem or None
        """
        if not self.loaded:
            self.load()
        return self.agents.get(agent_id)

    def get_ids(self) -> list:
        """
        Get list of custom agent IDs

        :return: list of agent IDs
        """
        if not self.loaded:
            self.load()
        return list(self.agents.keys())

    def get_schema(self, agent_id: str) -> list:
        """
        Get schema of a specific custom agent

        :param agent_id: agent ID
        :return: list with schema or empty list
        """
        if not self.loaded:
            self.load()
        agent = self.agents.get(agent_id)
        if agent:
            return agent.schema
        return []

    def build_options(self, agent_id: str) -> dict:
        """
        Build options for a specific custom agent

        :param agent_id: agent ID
        :return: dict with options or empty dict
        """
        if not self.loaded:
            self.load()

        agent = self.agents.get(agent_id)
        if not agent:
            return {}

        schema = agent.schema if agent else []
        options = {}
        for node in schema:
            try:
                if "type" in node and node["type"] == "agent":
                    if "id" in node:
                        sub_agent_id = node["id"]
                        tab = {
                            "label": sub_agent_id
                        }
                        opts = {
                            "model": {
                                "label": trans("agent.option.model"),
                                "type": "combo",
                                "use": "models",
                                "default": MODEL_DEFAULT,
                            }
                        }
                        if "slots" in node:
                            slots = node["slots"]
                            if "name" in slots and slots["name"]:
                                tab["label"] = slots["name"]
                            if "role" in slots:
                                opts["role"] = {
                                    "type": "text",
                                    "label": trans("agent.option.role.label"),
                                    "description": trans("agent.option.role"),
                                    "default": slots["role"],
                                }
                            if "instruction" in slots:
                                opts["prompt"] = {
                                    "type": "textarea",
                                    "label": trans("agent.option.prompt"),
                                    "default": slots["instruction"],
                                }
                            if "remote_tools" in slots:
                                opts["allow_remote_tools"] = {
                                    "type": "bool",
                                    "label": trans("agent.option.tools.remote"),
                                    "description": trans("agent.option.tools.remote.desc"),
                                    "default": slots["remote_tools"],
                                }
                            if "local_tools" in slots:
                                opts["allow_local_tools"] = {
                                    "type": "bool",
                                    "label": trans("agent.option.tools.local"),
                                    "description": trans("agent.option.tools.local.desc"),
                                    "default": slots["local_tools"],
                                }
                        tab["options"] = opts
                        options[sub_agent_id] = tab
            except Exception as e:
                self.window.core.debug.log(f"Failed to build options for custom agent '{agent_id}': {e}")
                continue

        # debug tab - trace_id, etc.
        """
        options["debug"] = {
            "label": trans("agent.tab.debug"),
            "options": {
                "trace_id": {
                    "type": "text",
                    "label": trans("agent.option.debug.trace_id"),
                    "description": trans("agent.option.debug.trace_id.desc"),
                    "default": "",
                }
            }
        }
        """
        return options

    def new_agent(self, name: str):
        """
        Create new custom agent

        :param name: agent name
        """
        if not self.loaded:
            self.load()
        new_id = str(uuid4())
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

    def update_agent(self, agent_id: str, layout: dict, schema: list):
        """
        Update layout and schema of a specific custom agent

        :param agent_id: agent ID
        :param layout: dictionary with new layout
        :param schema: list with new schema
        """
        if not self.loaded:
            self.load()
        agent = self.agents.get(agent_id)
        if agent:
            if layout is None:
                layout = {}
            if schema is None:
                schema = []
            agent.layout = layout
            agent.schema = schema
            self.save()