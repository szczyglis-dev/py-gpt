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

import json
import os
import uuid

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.provider.assistant.base import BaseProvider
from pygpt_net.provider.attachment.json_file import JsonFileProvider as AttachmentJsonFileProvider


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "assistant"
        self.config_file = 'assistants.json'

    def create_id(self):
        """
        Create unique uuid

        :return: uuid
        :rtype: str
        """
        return str(uuid.uuid4())

    def create(self, assistant):
        """
        Create new and return its ID

        :param assistant: AssistantItem
        :return: assistant ID
        :rtype: str
        """
        if assistant.id is None or assistant.id == "":
            assistant.id = self.create_id()
        return assistant.id

    def load(self):
        """Load assistants from file"""
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
                        assistant = AssistantItem()
                        self.deserialize(item, assistant)
                        items[id] = assistant
        except Exception as e:
            self.window.core.debug.log(e)
            items = {}

        return items

    def save(self, items):
        """
        Save assistants to file
        """
        try:
            # update assistants
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in items:
                assistant = items[id]
                ary[id] = self.serialize(assistant)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving assistants: {}".format(str(e)))

    def remove(self, id):
        """
        Delete by id

        :param id: id
        """
        pass

    def truncate(self):
        """Delete all"""
        pass

    def patch(self, version):
        """
        Migrate presets to current app version

        :param version: current app version
        :return: true if migrated
        :rtype: bool
        """
        return False

    @staticmethod
    def serialize(item):
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        :rtype: dict
        """
        # serialize attachments
        attachments = {}
        for id in item.attachments:
            attachment = item.attachments[id]
            attachments[id] = AttachmentJsonFileProvider.serialize(attachment)

        return {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'instructions': item.instructions,
            'model': item.model,
            'meta': item.meta,
            'attachments': attachments,
            'files': item.files,
            'tools': item.tools,
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
        if 'description' in data:
            item.description = data['description']
        if 'instructions' in data:
            item.instructions = data['instructions']
        if 'model' in data:
            item.model = data['model']
        if 'meta' in data:
            item.meta = data['meta']
        if 'files' in data:
            item.files = data['files']
        if 'tools' in data:
            item.tools = data['tools']

        # fix for older versions
        if 'function' in item.tools:
            if isinstance(item.tools['function'], bool):
                item.tools['function'] = []

        # deserialize attachments
        if 'attachments' in data:
            attachments = data['attachments']
            for id in attachments:
                ary = attachments[id]
                attachment = AttachmentItem()
                AttachmentJsonFileProvider.deserialize(ary, attachment)
                item.attachments[id] = attachment

    def dump(self, item):
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
