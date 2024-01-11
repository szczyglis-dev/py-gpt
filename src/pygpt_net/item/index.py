#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 04:00:00                  #
# ================================================== #

import json


class IndexItem:
    def __init__(self):
        """
        Index item
        """
        self.id = None
        self.name = None
        self.items = {}

    def serialize(self) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': self.id,
            'name': self.name,
            'items': self.items,
        }

    def deserialize(self, data: dict):
        """
        Deserialize item from dict

        :param data: serialized item
        """
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'items' in data:
            self.items = data['items']

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        return json.dumps(self.serialize())