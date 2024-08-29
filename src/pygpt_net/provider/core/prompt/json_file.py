#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.29 04:00:00                  #
# ================================================== #

import json
import os
import uuid

from packaging.version import Version

from pygpt_net.provider.core.prompt.base import BaseProvider
from pygpt_net.item.prompt import PromptItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "prompt"
        self.config_file = 'prompts.json'

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, prompt: PromptItem) -> str:
        """
        Create new and return its ID

        :param prompt: PromptItem
        :return: attachment ID
        """
        if prompt.id is None or prompt.id == "":
            prompt.id = self.create_id()
        return prompt.id

    def load(self) -> dict:
        """
        Load prompts from file

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
                    items = {}
                    for id in data['items']:
                        item = data['items'][id]
                        prompt = PromptItem()
                        self.deserialize(item, prompt)
                        items[id] = prompt
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}

        return items

    def save(self, items: dict):
        """
        Save prompts to file
        """
        try:
            # update prompts
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            ary = {}
            for id in items:
                prompt = items[id]
                ary[id] = self.serialize(prompt)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving prompts: {}".format(str(e)))

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

    def patch(self, version: Version) -> bool:
        """
        Migrate presets to current app version

        :param version: current app version
        :return: True if migrated
        """
        return False

    @staticmethod
    def serialize(prompt: PromptItem) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': prompt.id,
            'name': prompt.name,
            'content': prompt.content,
        }

    @staticmethod
    def deserialize(data: dict, prompt: PromptItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param prompt: PromptItem
        """
        if 'id' in data:
            prompt.id = data['id']
        if 'name' in data:
            prompt.name = data['name']
        if 'content' in data:
            prompt.content = data['content']

    def dump(self, item: PromptItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
