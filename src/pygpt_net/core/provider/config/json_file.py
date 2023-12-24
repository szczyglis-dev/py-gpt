#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import json
import os

from .base import BaseProvider


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "config"
        self.config_file = 'config.json'

    def get_version(self):
        """
        Get data version

        :return: version
        :rtype: str
        """
        path = os.path.join(self.path, self.config_file)
        with open(path, 'r', encoding="utf-8") as file:
            data = json.load(file)
            if data == "" or data is None:
                return
            if '__meta__' in data and 'version' in data['__meta__']:
                return data['__meta__']['version']

    def load(self, all=False):
        """
        Load config from JSON file

        :return: data
        :rtype: dict
        """
        data = {}
        path = os.path.join(self.path, self.config_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                if all:
                    print("Loaded config: {}".format(path))
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def load_base(self):
        """
        Load config from JSON file

        :return: data
        :rtype: dict
        """
        data = {}
        path = os.path.join(self.path_app, 'data', 'config', self.config_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                print("Loaded default app config: {}".format(path))
        except Exception as e:
            print("FATAL ERROR: {}".format(e))

        return data

    def save(self, data, filename='config.json'):
        """
        Save config to JSON file

        :param data: data to save
        :param filename: filename
        """
        path = os.path.join(self.path, filename)
        try:
            data['__meta__'] = self.meta
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))

    def remove(self, id):
        pass

    def truncate(self):
        pass

    @staticmethod
    def serialize(item):
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
    def deserialize(data, item):
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

    def dump(self, item):
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
