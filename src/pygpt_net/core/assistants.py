#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

import json
import os


class Assistants:
    def __init__(self, config=None):
        """
        Assistants

        :param config: config object
        """
        self.config = config
        self.config_file = 'assistants.json'
        self.items = {}

    def get_by_idx(self, idx):
        """
        Returns assistant by index

        :param idx: index
        :param mode: mode
        :return: assistant ID
        """
        assistants = self.get_all()
        return list(assistants.keys())[idx]

    def get_by_id(self, id):
        """
        Returns assistant by ID

        :param id: ID
        :return: assistant
        """
        assistants = self.get_all()
        return assistants[id]

    def get_all(self):
        """
        Returns assistants

        :return: assistants dict
        """
        return self.items

    def has(self, id):
        """
        Checks if assistant exists

        :param id: assistant ID
        :return: bool
        """
        return id in self.items

    def create(self):
        """
        Creates new assistant

        :return: assistant ID
        """
        assistant = AssistantItem()
        return assistant

    def add(self, assistant):
        """
        Adds iassistant

        :param assistant: item to add
        """
        id = assistant.id
        self.items[id] = assistant  # add assistant

        # save to file
        self.save()

    def delete(self, id):
        """
        Deletes assistant

        :param id: id of assistant
        """
        if id in self.items:
            self.items.pop(id)
        self.save()

    def rename_file(self, assistant_id, file_id, name):
        """
        Renames uploaded remote file name

        :param assistant_id: assistant_id
        :param file_id: file_id
        :param name: new name
        """
        assistant = self.get_by_id(assistant_id)
        if assistant is None:
            return
        if file_id in assistant.files:
            assistant.files[file_id]['name'] = name
            self.save()

    def get_default_assistant(self):
        """
        Returns default assistant

        :return: default assistant
        """
        assistants = self.get_all()
        if len(assistants) == 0:
            return None
        return list(assistants.keys())[0]

    def load(self):
        """Loads assistants from file"""
        path = os.path.join(self.config.path, self.config_file)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    file.close()
                    if data == "" or data is None or 'items' not in data:
                        self.items = {}
                        return
                    # deserialize
                    for id in data['items']:
                        assistant = data['items'][id]
                        item = AssistantItem()
                        item.deserialize(assistant)
                        self.items[id] = item
        except Exception as e:
            print(e)
            self.items = {}

    def save(self):
        """
        Saves assistants to file
        """
        try:
            # update assistants
            path = os.path.join(self.config.path, self.config_file)
            data = {}
            items = {}

            # serialize
            for uuid in self.items:
                assistant = self.items[uuid]
                items[uuid] = assistant.serialize()

            data['__meta__'] = self.config.append_meta()
            data['items'] = items
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

        except Exception as e:
            print("Error while saving assistants: {}".format(str(e)))


class AssistantItem:
    def __init__(self):
        """
        Assistant item
        """
        self.id = None
        self.name = None
        self.description = None
        self.instructions = None
        self.model = None
        self.meta = {}
        self.files = {}
        self.tools = {
            "code_interpreter": False,
            "retrieval": False,
            "function": False,
        }

    def reset(self):
        """
        Resets assistant
        """
        self.id = None
        self.name = None
        self.description = None
        self.instructions = None
        self.model = None
        self.meta = {}
        self.files = {}
        self.tools = {
            "code_interpreter": False,
            "retrieval": False,
            "function": False,
        }

    def has_tool(self, tool):
        """
        Checks if assistant has tool

        :param tool: tool name
        :return: bool
        """
        return tool in self.tools and self.tools[tool] is True

    def has_file(self, file_id):
        """
        Checks if assistant has file with ID

        :param file_id: file ID
        """
        return file_id in self.files

    def add_file(self, file_id):
        """
        Adds empty file to assistant

        :param file_id: file ID
        """
        self.files[file_id] = {}
        self.files[file_id]['id'] = file_id

    def delete_file(self, file_id):
        """
        Deletes file from assistant

        :param file_id: file ID
        """
        if file_id in self.files:
            self.files.pop(file_id)

    def serialize(self):
        """
        Serializes item to dict

        :return: serialized item
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'instructions': self.instructions,
            'model': self.model,
            'meta': self.meta,
            'files': self.files,
            'tools': self.tools,
        }

    def deserialize(self, data):
        """Deserializes item from dict"""
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'description' in data:
            self.description = data['description']
        if 'instructions' in data:
            self.instructions = data['instructions']
        if 'model' in data:
            self.model = data['model']
        if 'meta' in data:
            self.meta = data['meta']
        if 'files' in data:
            self.files = data['files']
        if 'tools' in data:
            self.tools = data['tools']

    def dump(self):
        """Dumps item to string"""
        return json.dumps(self.serialize())
