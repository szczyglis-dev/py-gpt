#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 01:00:00                  #
# ================================================== #

import copy
import json
import os
import uuid

from packaging.version import Version

from pygpt_net.provider.core.index.base import BaseProvider
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

    def load(self, store_id: str = None) -> dict:
        """
        Load indexes from file

        :param store_id: store ID
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

                    is_patch = False
                    # patch for old versions < 2.0.114
                    if len(data['items']) > 0 and "store" not in data['items']:
                        old_data = copy.deepcopy(data['items'])
                        data['items'] = {}
                        data['items']['store'] = {}
                        data['items']['store']['SimpleVectorStore'] = old_data
                        is_patch = True

                    # deserialize
                    for store_id in data['items']['store']:
                        items[store_id] = {}
                        for idx_id in data['items']['store'][store_id]:
                            item = data['items']['store'][store_id][idx_id]
                            index = IndexItem()
                            self.deserialize(item, index)
                            if index.store is None or index.store == "":
                                index.store = store_id
                            items[store_id][idx_id] = index

                    # patch for old versions < 2.0.114
                    if is_patch:
                        self.save(items)

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
            for store in items:
                ary[store] = {}
                for file_id in items[store]:
                    index = items[store][file_id]
                    ary[store][file_id] = self.serialize(index)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = {
                'store': ary,
            }
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

    def truncate(self, store_id: str, idx: str):
        """
        Delete all

        :param store_id: store ID
        :param idx: index ID
        """
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
            items = {'SimpleVectorStore': {}}
            item = IndexItem()
            item.id = "base"
            item.name = "base"
            items['SimpleVectorStore'][item.id] = item
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
            'store': index.store,
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
        if 'store' in data:
            index.store = data['store']
        if 'items' in data:
            index.items = data['items']

        # append name key from file id
        for item_id in index.items:
             index.items[item_id]["name"] = item_id

    def dump(self, item: IndexItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
