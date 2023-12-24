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
import uuid

from .base import BaseProvider
from ...item.attachment import AttachmentItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "attachment"
        self.config_file = 'attachments.json'

    def create_id(self):
        """
        Create unique uuid

        :return: uuid
        :rtype: str
        """
        return str(uuid.uuid4())

    def create(self, attachment):
        """
        Create new and return its ID

        :param attachment: AttachmentItem
        :return: attachment ID
        :rtype: str
        """
        if attachment.id is None or attachment.id == "":
            attachment.id = self.create_id()
        return attachment.id

    def load(self):
        """Load attachments from file"""
        path = os.path.join(self.window.app.config.path, self.config_file)
        items = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return {}
                    # deserialize
                    for mode in data['items']:
                        items[mode] = {}
                        for id in data['items'][mode]:
                            item = data['items'][mode][id]
                            attachment = AttachmentItem()
                            self.deserialize(item, attachment)
                            items[mode][id] = attachment
        except Exception as e:
            self.window.app.debug.log(e)
            items = {}

        return items

    def save(self, items):
        """
        Save attachments to file
        """
        try:
            # update attachments
            path = os.path.join(self.window.app.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for mode in items:
                ary[mode] = {}
                for id in items[mode]:
                    attachment = items[mode][id]
                    ary[mode][id] = self.serialize(attachment)

            data['__meta__'] = self.window.app.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.app.debug.log(e)
            print("Error while saving attachments: {}".format(str(e)))

    def remove(self, id):
        """
        Delete by id

        :param id: id
        """
        pass

    def truncate(self, mode):
        """Delete all"""
        path = os.path.join(self.window.app.config.path, self.config_file)
        data = {'__meta__': self.window.app.config.append_meta(), 'items': {}}
        try:
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.app.debug.log(e)

    def patch(self, version):
        """
        Migrate presets to current app version

        :param version: current app version
        :return: true if migrated
        :rtype: bool
        """
        return False

    @staticmethod
    def serialize(attachment):
        """
        Serialize item to dict

        :return: serialized item
        :rtype: dict
        """
        return {
            'id': attachment.id,
            'name': attachment.name,
            'path': attachment.path,
            'remote': attachment.remote,
            'send': attachment.send
        }

    @staticmethod
    def deserialize(data, attachment):
        """
        Deserialize item from dict

        :param data: serialized item
        :param attachment: AttachmentItem
        """
        if 'id' in data:
            attachment.id = data['id']
        if 'name' in data:
            attachment.name = data['name']
        if 'path' in data:
            attachment.path = data['path']
        if 'remote_id' in data:
            attachment.remote = data['remote']
        if 'send' in data:
            attachment.send = data['send']

    def dump(self, item):
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
