#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import json
import os
import uuid

from pygpt_net.item.assistant import AssistantStoreItem
from pygpt_net.provider.core.assistant.base import BaseProvider


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "assistant_store"
        self.config_file = 'assistants_vector_store.json'

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, store: AssistantStoreItem) -> str:
        """
        Create new and return its ID

        :param store: AssistantStoreItem
        :return: vector store ID
        """
        if store.id is None or store.id == "":
            store.id = self.create_id()
        return store.id

    def load(self) -> dict:
        """
        Load assistants vector store from file

        :return: dict of assistants vector store
        """
        items = {}
        path = os.path.join(self.window.core.config.path, self.config_file)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return {}
                    # deserialize
                    for id in data['items']:
                        item = data['items'][id]
                        store = AssistantStoreItem()
                        self.deserialize(item, store)
                        items[id] = store
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}
        return items

    def save(self, items: dict):
        """
        Save assistants vector store to file

        :param items: dict of assistants vector store
        """
        try:
            # update store
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in items:
                store = items[id]
                ary[id] = self.serialize(store)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving assistants vector store: {}".format(str(e)))

    def remove(self, id: str):
        """
        Delete by id

        :param id: id
        """
        pass

    def truncate(self):
        """Delete all"""
        pass

    @staticmethod
    def serialize(item: AssistantStoreItem) -> dict:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        """
        return {
            'id': item.id,
            'name': item.name,
            'status': item.status,
            'file_ids': item.file_ids,
        }

    @staticmethod
    def deserialize(data: dict, item: AssistantStoreItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'id' in data:
            item.id = data['id']
        if 'name' in data:
            item.name = data['name']
        if 'status' in data:
            item.status = data['status']
        if 'file_ids' in data:
            item.file_ids = data['file_ids']

    def dump(self, item: AssistantStoreItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
