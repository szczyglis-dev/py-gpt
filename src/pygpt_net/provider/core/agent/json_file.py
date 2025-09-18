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

import json
import os
import uuid
from typing import Dict, Any

from packaging.version import Version

from pygpt_net.item.agent import AgentItem
from pygpt_net.item.builder_layout import BuilderLayoutItem

from .base import BaseProvider

class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "agent"
        self.config_file = 'agents.json'

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, agent: AgentItem) -> str:
        """
        Create new and return its ID

        :param agent: custom gent
        :return: agent ID
        """
        if agent.id is None or agent.id == "":
            agent.id = self.create_id()
        return agent.id

    def load(self) -> Dict[str, Any]:
        """
        Load custom agents from file

        :return: dict with layout and agents
        """
        items = {}
        layout = None
        path = os.path.join(self.window.core.config.path, self.config_file)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None:
                        return {}
                    if "layout" in data:
                        layout = BuilderLayoutItem()
                        self.deserialize_layout(data['layout'], layout)
                    if "items" in data:
                        for id in data['items']:
                            agent = AgentItem()
                            item = data['items'][id]
                            self.deserialize(item, agent)
                            items[id] = agent
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}

        return {
            "layout": layout,
            "agents": items,
        }

    def save(self, layout: BuilderLayoutItem, agents: Dict[str, AgentItem]):
        """
        Save custom agents to file

        :param layout: layout dict
        :param agents: dict of agents
        """
        try:
            # update agents
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in agents:
                agent = agents[id]
                ary[id] = self.serialize(agent)

            data['__meta__'] = self.window.core.config.append_meta()
            data["layout"] = self.serialize_layout(layout)
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving agents: {}".format(str(e)))

    def remove(self, id: str):
        """
        Delete by id

        :param id: id
        """
        pass

    def truncate(self):
        """Delete all"""
        pass

    def patch(self, version: Version) -> bool:
        """
        Migrate presets to current app version

        :param version: current app version
        :return: True if migrated
        """
        return False

    @staticmethod
    def serialize(item: AgentItem) -> Dict[str, Any]:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        """
        return {
            'id': item.id,
            'name': item.name,
            'layout': item.layout,
        }

    @staticmethod
    def deserialize(data: Dict[str, Any], item: AgentItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'id' in data:
            item.id = data['id']
        if 'name' in data:
            item.name = data['name']
        if "layout" in data:
            item.layout = data['layout']

    @staticmethod
    def serialize_layout(item: BuilderLayoutItem) -> Dict[str, Any]:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        """
        return {
            'id': item.id,
            'name': item.name,
            'data': item.data,
        }

    @staticmethod
    def deserialize_layout(data: Dict[str, Any], item: BuilderLayoutItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'id' in data:
            item.id = data['id']
        if 'name' in data:
            item.name = data['name']
        if "data" in data:
            item.data = data['data']

    def dump(self, item: AgentItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
