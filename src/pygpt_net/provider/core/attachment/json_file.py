#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

import json
import os
import uuid
from typing import Dict

from packaging.version import Version

from pygpt_net.provider.core.attachment.base import BaseProvider
from pygpt_net.item.attachment import AttachmentItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "attachment"
        self.config_file = 'attachments.json'

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, attachment: AttachmentItem) -> str:
        """
        Create new and return its ID

        :param attachment: AttachmentItem
        :return: attachment ID
        """
        if attachment.id is None or attachment.id == "":
            attachment.id = self.create_id()
        return attachment.id

    def load(self) -> Dict[str, Dict[str, AttachmentItem]]:
        """
        Load attachments from file

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
                    for mode in data['items']:
                        items[mode] = {}
                        for id in data['items'][mode]:
                            item = data['items'][mode][id]
                            attachment = AttachmentItem()
                            self.deserialize(item, attachment)
                            items[mode][id] = attachment
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}

        return items

    def save(self, items: Dict[str, Dict[str, AttachmentItem]]):
        """
        Save attachments to file
        """
        try:
            # update attachments
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for mode in items:
                ary[mode] = {}
                for id in items[mode]:
                    attachment = items[mode][id]
                    ary[mode][id] = self.serialize(attachment)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving attachments: {}".format(str(e)))

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
    def serialize(attachment: AttachmentItem) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': attachment.id,
            'name': attachment.name,
            'path': attachment.path,
            'remote': attachment.remote,
            'send': attachment.send,
            'vector_store_ids': attachment.vector_store_ids,
            'type': attachment.type,
            'extra': attachment.extra,
        }

    @staticmethod
    def deserialize(data: dict, attachment: AttachmentItem):
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
        if 'vector_store_ids' in data:
            attachment.vector_store_ids = data['vector_store_ids']
        if 'type' in data:
            attachment.type = data['type']
        if 'extra' in data:
            attachment.extra = data['extra']

    def dump(self, item: AttachmentItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
