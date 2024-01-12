#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 04:00:00                  #
# ================================================== #

import json
import os
import uuid

from packaging.version import Version

from pygpt_net.provider.index.base import BaseProvider
from pygpt_net.item.index import IndexItem
from .patch import Patch


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "json_file"
        self.type = "index"
        self.config_file = 'indexes.json'

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, index: IndexItem) -> str:
        """
        Create new and return its ID

        :param index: IndexItem
        :return: index ID
        """
        if index.id is None or index.id == "":
            index.id = self.create_id()
        return index.id

    def load(self) -> dict:
        """
        Load indexes from file

        :return: dict
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        items = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return {}
                    # deserialize
                    for id in data['items']:
                        item = data['items'][id]
                        index = IndexItem()
                        self.deserialize(item, index)
                        items[id] = index
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}

        return items

    def save(self, items: dict):
        """
        Save indexes to file
        """
        try:
            # update indexes
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in items:
                index = items[id]
                ary[id] = self.serialize(index)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving indexes: {}".format(str(e)))

    def remove(self, id: str):
        """
        Delete by id

        :param id: id
        """
        pass

    def truncate(self, mode: str):
        """Delete all"""
        path = os.path.join(self.window.core.config.path, self.config_file)
        data = {'__meta__': self.window.core.config.append_meta(), 'items': {}}
        try:
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.core.debug.log(e)

    def install(self) -> bool:
        """
        Install provider
        :return: True if success
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        if not os.path.exists(path):
            items = {}
            item = IndexItem()
            item.id = "base"
            item.name = "base"
            items[item.id] = item
            self.save(items)
        return True

    def patch(self, version: Version) -> bool:
        """
        Migrate presets to current app version

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)

    @staticmethod
    def serialize(index: IndexItem) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': index.id,
            'name': index.name,
            'items': index.items
        }

    @staticmethod
    def deserialize(data: dict, index: IndexItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param index: IndexItem
        """
        if 'id' in data:
            index.id = data['id']
        if 'name' in data:
            index.name = data['name']
        if 'items' in data:
            index.items = data['items']

    def dump(self, item: IndexItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
