#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import json
import os
from typing import Optional, Dict

from pygpt_net.provider.core.mode.base import BaseProvider
from pygpt_net.item.mode import ModeItem
from .patch import Patch


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "json_file"
        self.type = "mode"
        self.config_file = 'modes.json'

    def get_version(self) -> Optional[str]:
        """
        Get data version

        :return: version
        """
        path = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', self.config_file)
        with open(path, 'r', encoding="utf-8") as file:
            data = json.load(file)
            if data == "" or data is None:
                return
            if '__meta__' in data and 'version' in data['__meta__']:
                return data['__meta__']['version']

    def load(self) -> Optional[Dict[str, ModeItem]]:
        """
        Load modes config from JSON file

        :return: models dict
        """
        items = {}
        path = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', self.config_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                if data == "" or data is None or 'items' not in data:
                    return {}

                # deserialize
                for id in data['items']:
                    item = data['items'][id]
                    model = ModeItem()
                    self.deserialize(item, model)
                    items[id] = model

        except Exception as e:
            self.window.core.debug.log(e)

        return items

    def save(self, items: Dict[str, ModeItem]):
        """
        Save modes config to JSON file

        :param items: models dict
        """
        path = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', self.config_file)
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

    @staticmethod
    def serialize(item: ModeItem) -> Dict[str, str]:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        :rtype: dict
        """
        return {
            'id': item.id,
            'name': item.name,
            'label': item.label,
        }

    @staticmethod
    def deserialize(data: Dict[str, str], item: ModeItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'id' in data:
            item.id = data['id']
        if 'name' in data:
            item.name = data['name']
        if 'label' in data:
            item.label = data['label']

    def dump(self, item: ModeItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
