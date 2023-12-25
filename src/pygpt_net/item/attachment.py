#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

class AttachmentItem:
    def __init__(self):
        """
        Attachment item
        """
        self.name = None
        self.id = None
        self.path = None
        self.remote = None
        self.send = False

    def serialize(self):
        """
        Serialize item to dict

        :return: serialized item
        :rtype: dict
        """
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'remote': self.remote,
            'send': self.send
        }

    def deserialize(self, data):
        """
        Deserialize item from dict

        :param data: serialized item
        """
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'path' in data:
            self.path = data['path']
        if 'remote_id' in data:
            self.remote = data['remote']
        if 'send' in data:
            self.send = data['send']

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        return json.dumps(self.serialize())