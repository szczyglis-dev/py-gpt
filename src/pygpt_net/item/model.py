#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 22:00:00                  #
# ================================================== #

import json


class ModelItem:
    def __init__(self, id=None):
        """
        Model data item

        :param id: Model ID
        """
        self.id = id
        self.name = None
        self.mode = []
        self.langchain = {}
        self.llama_index = {}
        self.ctx = 0
        self.tokens = 0
        self.default = False

    def from_dict(self, data: dict):
        """
        Load data from dict

        :param data: dict
        """
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'mode' in data:
            mode = data['mode'].replace(' ', '')
            self.mode = mode.split(',')
        if 'ctx' in data:
            self.ctx = data['ctx']
        if 'tokens' in data:
            self.tokens = data['tokens']
        if 'default' in data:
            self.default = data['default']

        # langchain
        if 'langchain.provider' in data:
            self.langchain['provider'] = data['langchain.provider']
        if 'langchain.mode' in data:
            if data['langchain.mode'] is None or data['langchain.mode'] == "":
                self.langchain['mode'] = []
            else:
                mode = data['langchain.mode'].replace(' ', '')
                self.langchain['mode'] = mode.split(',')
        if 'langchain.args' in data:
            self.langchain['args'] = data['langchain.args']
        if 'langchain.env' in data:
            self.langchain['env'] = data['langchain.env']

        # llama index
        if 'llama_index.provider' in data:
            self.llama_index['provider'] = data['llama_index.provider']
        if 'llama_index.mode' in data:
            if data['llama_index.mode'] is None or data['llama_index.mode'] == "":
                self.llama_index['mode'] = []
            else:
                mode = data['llama_index.mode'].replace(' ', '')
                self.llama_index['mode'] = mode.split(',')
        if 'llama_index.args' in data:
            self.llama_index['args'] = data['llama_index.args']
        if 'llama_index.env' in data:
            self.llama_index['env'] = data['llama_index.env']

    def to_dict(self) -> dict:
        """
        Return data as dict

        :return: dict
        """
        data = {}
        data['id'] = self.id
        data['name'] = self.name
        data['mode'] = ','.join(self.mode)
        data['langchain'] = self.langchain
        data['ctx'] = self.ctx
        data['tokens'] = self.tokens
        data['default'] = self.default

        data['langchain.provider'] = None
        data['langchain.mode'] = ""
        data['langchain.args'] = []
        data['langchain.env'] = []
        data['llama_index.provider'] = None
        data['llama_index.mode'] = ""
        data['llama_index.args'] = []
        data['llama_index.env'] = []

        # langchain
        if 'provider' in self.langchain:
            data['langchain.provider'] = self.langchain['provider']
        if 'mode' in self.langchain:
            data['langchain.mode'] = ",".join(self.langchain['mode'])
        if 'args' in self.langchain:
            # old versions support
            if isinstance(self.langchain['args'], dict):
                for key, value in self.langchain['args'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    item['type'] = 'str'
                    data['langchain.args'].append(item)
            elif isinstance(self.langchain['args'], list):
                data['langchain.args'] = self.langchain['args']
        if 'env' in self.langchain:
            # old versions support
            if isinstance(self.langchain['env'], dict):
                for key, value in self.langchain['env'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    data['langchain.env'].append(item)
            elif isinstance(self.langchain['env'], list):
                data['langchain.env'] = self.langchain['env']

        # llama_index
        if 'provider' in self.llama_index:
            data['llama_index.provider'] = self.llama_index['provider']
        if 'mode' in self.llama_index:
            data['llama_index.mode'] = ",".join(self.llama_index['mode'])
        if 'args' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['args'], dict):
                for key, value in self.llama_index['args'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    item['type'] = 'str'
                    data['llama_index.args'].append(item)
            elif isinstance(self.llama_index['args'], list):
                data['llama_index.args'] = self.llama_index['args']
        if 'env' in self.llama_index:
            # old versions support
            if isinstance(self.llama_index['env'], dict):
                for key, value in self.llama_index['env'].items():
                    item = {}
                    item['name'] = key
                    item['value'] = value
                    data['llama_index.env'].append(item)
            elif isinstance(self.llama_index['env'], list):
                data['llama_index.env'] = self.llama_index['env']

        return data

    def is_supported(self, mode: str) -> bool:
        """
        Check if model supports mode

        :param mode: Mode
        :return: True if supported
        """
        return mode in self.mode

    def has_mode(self, mode: str) -> bool:
        """
        Check if model has mode

        :param mode: Mode
        :return: True if supported
        """
        return mode in self.mode

    def add_mode(self, mode: str):
        """
        Add mode

        :param mode: Mode
        """
        if mode not in self.mode:
            self.mode.append(mode)

    def remove_mode(self, mode: str):
        """
        Remove mode

        :param mode: Mode
        """
        if mode in self.mode:
            self.mode.remove(mode)

    def dump(self) -> str:
        """
        Dump event to json string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()
