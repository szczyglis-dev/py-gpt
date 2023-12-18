#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #

import json
import os

from .attachments import AttachmentItem


class Assistants:
    def __init__(self, window=None):
        """
        Assistants

        :param window: Window instance
        """
        self.window = window
        self.config_file = 'assistants.json'
        self.current_file = None
        self.items = {}

    def get_by_idx(self, idx):
        """
        Return assistant by index

        :param idx: index
        :return: assistant ID
        :rtype: str
        """
        assistants = self.get_all()
        return list(assistants.keys())[idx]

    def get_by_id(self, id):
        """
        Return assistant by ID

        :param id: ID
        :return: assistant
        :rtype: AssistantItem
        """
        assistants = self.get_all()
        if id not in assistants:
            return None
        return assistants[id]

    def get_all(self):
        """
        Return assistants

        :return: assistants dict
        :rtype: dict
        """
        return self.items

    def has(self, id):
        """
        Check if assistant exists

        :param id: assistant ID
        :return: bool
        :rtype: bool
        """
        return id in self.items

    def create(self):
        """
        Create new assistant item

        :return: assistant ID
        :rtype: AssistantItem
        """
        assistant = AssistantItem()
        return assistant

    def add(self, assistant):
        """
        Add assistant

        :param assistant: item to add
        """
        id = assistant.id
        self.items[id] = assistant  # add assistant

        # save to file
        self.save()

    def delete(self, id):
        """
        Delete assistant

        :param id: id of assistant
        """
        if id in self.items:
            self.items.pop(id)
        self.save()

    def rename_file(self, assistant, file_id, name):
        """
        Rename uploaded remote file name

        :param assistant: assistant object
        :param file_id: file_id
        :param name: new name
        """
        if assistant is None:
            return

        need_save = False

        # rename file in files
        if file_id in assistant.files:
            assistant.files[file_id]['name'] = name  # TODO: make object
            need_save = True

        # rename file in attachments
        if file_id in assistant.attachments:
            assistant.attachments[file_id].name = name
            need_save = True

        # save assistants
        if need_save:
            self.save()

    def replace_attachment(self, assistant, attachment, old_id, new_id):
        """
        Replace temporary attachment with uploaded one

        :param assistant: assistant object
        :param old_id: old id
        :param new_id: new id
        """
        if old_id in assistant.attachments:
            assistant.attachments[new_id] = attachment
            del assistant.attachments[old_id]
            self.save()

    def get_default_assistant(self):
        """
        Return default assistant

        :return: default assistant
        :rtype: AssistantItem or None
        """
        assistants = self.get_all()
        if len(assistants) == 0:
            return None
        return list(assistants.keys())[0]

    def get_file_id_by_idx(self, assistant, idx):
        """
        Return file ID by index

        :param assistant: assistant object
        :param idx: index
        :return: file ID
        :rtype: str
        """
        files = assistant.files
        return list(files.keys())[idx]

    def get_file_by_id(self, assistant, id):
        """
        Return file by ID

        :param assistant: assistant object
        :param id: file ID
        :return: Dict with file data
        :rtype: dict or None
        """
        files = assistant.files
        return files[id]

    def import_files(self, assistant, data):
        """
        Import files from remote API

        :param assistant: assistant object
        :param data: data from remote API
        """
        if assistant is None:
            return

        remote_ids = []
        # add files from data (from remote)
        for file in data:
            id = file.id
            remote_ids.append(id)
            name = ""
            path = ""
            if id in assistant.files:
                if 'name' in assistant.files[id] and assistant.files[id]['name'] != '':
                    name = assistant.files[id]['name']
                else:
                    name = id
                if 'path' in assistant.files[id]:
                    path = assistant.files[id]['path']
            elif id in assistant.attachments:
                name = assistant.attachments[id].name
                path = assistant.attachments[id].path
            else:
                name = id
                path = None
            assistant.files[id] = {
                'id': id,
                'name': name,
                'path': path,
            }

        # remove files that are not in data (from remote)
        for id in list(assistant.files.keys()):
            if id not in remote_ids:
                del assistant.files[id]

    def load(self):
        """Load assistants from file"""
        path = os.path.join(self.window.config.path, self.config_file)
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
        Save assistants to file
        """
        try:
            # update assistants
            path = os.path.join(self.window.config.path, self.config_file)
            data = {}
            items = {}

            # serialize
            for uuid in self.items:
                assistant = self.items[uuid]
                items[uuid] = assistant.serialize()

            data['__meta__'] = self.window.config.append_meta()
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
        self.files = {}  # files IDs (uploaded to remote storage)
        self.attachments = {}  # attachments (local)
        self.tools = {
            "code_interpreter": False,
            "retrieval": False,
            "function": [],
        }

    def reset(self):
        """
        Reset assistant
        """
        self.id = None
        self.name = None
        self.description = None
        self.instructions = None
        self.model = None
        self.meta = {}
        self.files = {}
        self.attachments = {}
        self.tools = {
            "code_interpreter": False,
            "retrieval": False,
            "function": [],
        }

    def add_function(self, name, parameters, desc):
        """
        Add function to assistant

        :param name: function name
        :param parameters: function parameters (JSON encoded)
        :param desc: function description
        """
        function = {
            'name': name,
            'params': parameters,
            'desc': desc,
        }
        self.tools['function'].append(function)

    def has_functions(self):
        """
        Check if assistant has functions

        :return: bool
        :rtype: bool
        """
        return len(self.tools['function']) > 0

    def get_functions(self):
        """
        Return assistant functions

        :return: functions
        :rtype: list
        """
        return self.tools['function']

    def has_tool(self, tool):
        """
        Check if assistant has tool

        :param tool: tool name
        :return: bool
        :rtype: bool
        """
        return tool in self.tools and self.tools[tool] is True

    def has_file(self, file_id):
        """
        Check if assistant has file with ID

        :param file_id: file ID
        :return: bool
        """
        return file_id in self.files

    def add_file(self, file_id):
        """
        Add empty file to assistant

        :param file_id: file ID
        """
        self.files[file_id] = {}
        self.files[file_id]['id'] = file_id

    def delete_file(self, file_id):
        """
        Delete file from assistant

        :param file_id: file ID
        """
        if file_id in self.files:
            self.files.pop(file_id)

    def clear_files(self):
        """
        Clear files
        """
        self.files = {}

    def has_attachment(self, attachment_id):
        """
        Check if assistant has attachment with ID

        :param attachment_id: attachment ID
        :return: bool
        :rtype: bool
        """
        return attachment_id in self.attachments

    def add_attachment(self, attachment):
        """
        Add attachment to assistant

        :param attachment: attachment
        """
        id = attachment.id
        self.attachments[id] = attachment

    def delete_attachment(self, attachment_id):
        """
        Delete attachment from assistant

        :param attachment_id: attachment ID
        """
        if attachment_id in self.attachments:
            self.attachments.pop(attachment_id)

    def clear_attachments(self):
        """
        Clear attachments
        """
        self.attachments = {}

    def serialize(self):
        """
        Serialize item to dict

        :return: serialized item
        :rtype: dict
        """
        # serialize attachments
        attachments = {}
        for id in self.attachments:
            attachment = self.attachments[id]
            attachments[id] = attachment.serialize()

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'instructions': self.instructions,
            'model': self.model,
            'meta': self.meta,
            'attachments': attachments,
            'files': self.files,
            'tools': self.tools,
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

        # fix for older versions
        if 'function' in self.tools:
            if isinstance(self.tools['function'], bool):
                self.tools['function'] = []

        # deserialize attachments
        if 'attachments' in data:
            attachments = data['attachments']
            for id in attachments:
                attachment = attachments[id]
                item = AttachmentItem()
                item.deserialize(attachment)
                self.attachments[id] = item

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        return json.dumps(self.serialize())
