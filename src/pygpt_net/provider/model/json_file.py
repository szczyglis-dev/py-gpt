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
import shutil
from packaging.version import parse as parse_version, Version

from pygpt_net.provider.model.base import BaseProvider
from pygpt_net.item.model import ModelItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "model"
        self.config_file = 'models.json'

    def install(self):
        """
        Install provider data files
        """
        dst = os.path.join(self.window.core.config.path, self.config_file)
        if not os.path.exists(dst):
            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', self.config_file)
            shutil.copyfile(src, dst)

    def get_version(self) -> str | None:
        """
        Get data version

        :return: version
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        with open(path, 'r', encoding="utf-8") as file:
            data = json.load(file)
            if data == "" or data is None:
                return
            if '__meta__' in data and 'version' in data['__meta__']:
                return data['__meta__']['version']

    def load(self) -> dict | None:
        """
        Load models config from JSON file
        """
        items = {}
        path = os.path.join(self.window.core.config.path, self.config_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                if data == "" or data is None:
                    return {}

                # migrate from old versions < 2.0.49
                if 'items' not in data:
                    for id in data:
                        if id == '__meta__':
                            continue
                        item = data[id]
                        model = ModelItem()
                        self.deserialize(item, model)
                        items[id] = model
                    items = dict(sorted(items.items(), key=lambda item: item[0]))  # sort by key
                    print("Loaded models: {}".format(path))
                    print("Migrating old version: {}".format(path))
                    self.save(items)
                    return items

                # deserialize
                for id in data['items']:
                    item = data['items'][id]
                    model = ModelItem()
                    self.deserialize(item, model)
                    items[id] = model
                print("Loaded models: {}".format(path))

        except Exception as e:
            self.window.core.debug.log(e)

        return items

    def save(self, items: dict):
        """
        Save models config to JSON file

        :param items: models dict
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        try:
            data = {}
            ary = {}

            # serialize
            for id in items:
                model = items[id]
                ary[id] = self.serialize(model)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)

    def remove(self, id: str):
        pass

    def truncate(self):
        pass

    def patch(self, version: Version) -> bool:
        """
        Migrate models to current app version

        :param version: current app version
        :return: True if updated
        """
        data = self.window.core.models.items
        updated = False

        # get version of models config
        current = self.window.core.models.get_version()
        old = parse_version(current)

        # check if models file is older than current app version
        if old < version:

            # < 0.9.1
            if old < parse_version("0.9.1"):
                # apply meta only (not attached in 0.9.0)
                print("Migrating models from < 0.9.1...")
                updated = True

            # < 2.0.1
            if old < parse_version("2.0.1"):
                print("Migrating models from < 2.0.1...")
                self.window.core.updater.patch_file('models.json', True)  # force replace file
                self.window.core.models.load()
                data = self.window.core.models.items
                updated = True

            # < 2.0.96  <--- patch for llama-index modes
            if old < parse_version("2.0.96"):
                print("Migrating models from < 2.0.96...")
                self.window.core.updater.patch_file('models.json', True)  # force replace file
                self.window.core.models.load()
                data = self.window.core.models.items
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.models.items = data
            self.window.core.models.save()

        return updated

    @staticmethod
    def serialize(item: ModelItem) -> dict:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        """
        return {
            'id': item.id,
            'name': item.name,
            'mode': item.mode,
            'langchain': item.langchain,
            'ctx': item.ctx,
            'tokens': item.tokens,
            'default': item.default,
        }

    @staticmethod
    def deserialize(data: dict, item: ModelItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'id' in data:
            item.id = data['id']
        if 'name' in data:
            item.name = data['name']
        if 'mode' in data:
            item.mode = data['mode']
        if 'langchain' in data:
            item.langchain = data['langchain']
        if 'ctx' in data:
            item.ctx = data['ctx']
        if 'tokens' in data:
            item.tokens = data['tokens']
        if 'default' in data:
            item.default = data['default']

    def dump(self, item: ModelItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
