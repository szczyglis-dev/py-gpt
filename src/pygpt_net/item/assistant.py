#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

import json
import time

from pygpt_net.item.attachment import AttachmentItem


class AssistantItem:
    def __init__(self):
        """Assistant item"""
        self.id = None
        self.name = None
        self.description = None
        self.instructions = None
        self.model = None
        self.meta = {}
        self.files = {}  # file IDs (files uploaded to remote storage)
        self.attachments = {}  # local attachments
        self.vector_store = "" # vector store ID
        self.tools = {
            "code_interpreter": False,
            "file_search": False,
            "function": [],
        }

    def reset(self):
        """Reset assistant"""
        self.id = None
        self.name = None
        self.description = None
        self.instructions = None
        self.model = None
        self.meta = {}
        self.files = {}
        self.attachments = {}
        self.vector_store = ""
        self.tools = {
            "code_interpreter": False,
            "file_search": False,
            "function": [],
        }

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "model": self.model,
            "meta": self.meta,
            "files": self.files,
            "attachments": self.attachments,
            "vector_store": self.vector_store,
            "tool.code_interpreter": self.tools["code_interpreter"],
            "tool.file_search": self.tools["file_search"],
            "tool.function": self.tools["function"],
        }

    def clear_functions(self):
        """Clear functions"""
        self.tools['function'] = []

    def clear_tools(self):
        """Clear tools"""
        self.tools = {
            "code_interpreter": False,
            "file_search": False,
            "function": [],
        }

    def add_function(self, name: str, parameters: str, desc: str):
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

    def has_functions(self) -> bool:
        """
        Check if assistant has functions

        :return: True if has functions
        """
        return len(self.tools['function']) > 0

    def get_functions(self) -> list:
        """
        Return assistant functions

        :return: functions list
        """
        return self.tools['function']

    def has_tool(self, tool: str) -> bool:
        """
        Check if assistant has tool

        :param tool: tool name
        :return: bool
        """
        return tool in self.tools and self.tools[tool] is True

    def has_file(self, id: str) -> bool:
        """
        Check if assistant has file with ID

        :param id: file ID
        :return: True if has file
        """
        return id in self.files

    def add_file(self, id: str):
        """
        Add empty file to assistant

        :param id: file ID
        """
        self.files[id] = {}
        self.files[id]['id'] = id

    def delete_file(self, file_id: str):
        """
        Delete file from assistant

        :param file_id: file ID
        """
        if file_id in self.files:
            self.files.pop(file_id)

    def clear_files(self):
        """Clear files dict"""
        self.files = {}

    def has_attachment(self, id: str) -> bool:
        """
        Check if assistant has attachment with ID

        :param id: attachment ID
        :return: True if has attachment
        """
        return id in self.attachments

    def add_attachment(self, attachment: AttachmentItem):
        """
        Add attachment to assistant

        :param attachment: attachment
        """
        id = attachment.id
        self.attachments[id] = attachment

    def delete_attachment(self, id: str):
        """
        Delete attachment from assistant

        :param id: attachment ID
        """
        if id in self.attachments:
            self.attachments.pop(id)

    def clear_attachments(self):
        """Clear attachments dict"""
        self.attachments = {}

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()


class AssistantStoreItem:
    def __init__(self):
        """Assistant vector store item"""
        self.id = None
        self.record_id = None
        self.uuid = None
        self.name = None
        self.description = None
        self.status = {}
        self.last_status = ""
        self.expire_days = 0
        self.usage_bytes = 0
        self.bytes = 0
        self.num_files = 0
        self.is_thread = False
        self.created = int(time.time())
        self.updated = int(time.time())
        self.last_active = int(time.time())
        self.last_sync = int(time.time())

    def reset(self):
        """Reset store"""
        self.id = None
        self.record_id = None
        self.uuid = None
        self.name = None
        self.description = None
        self.status = {}
        self.last_status = ""
        self.expire_days = 0
        self.usage_bytes = 0
        self.num_files = 0
        self.bytes = 0
        self.is_thread = False
        self.last_active = int(time.time())
        self.last_sync = int(time.time())

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "description": self.description,
            "last_status": self.last_status,
            "expire_days": self.expire_days,
            "usage_bytes": self.usage_bytes,
            "num_files": self.num_files,
            "status": self.status,
            "is_thread": self.is_thread,
        }

    def from_dict(self, data: dict):
        """
        Load from dictionary

        :param data: dictionary
        """
        self.id = data.get('id', None)
        self.name = data.get('name', None)
        self.uuid = data.get('uuid', None)
        self.expire_days = data.get('expire_days', 0)
        self.status = data.get('status', {})

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()


class AssistantFileItem:
    def __init__(self):
        """Assistant file item"""
        self.id = None
        self.record_id = None
        self.name = None
        self.path = None
        self.file_id = None
        self.store_id = None
        self.thread_id = None
        self.uuid = None
        self.size = 0
        self.created = 0
        self.updated = 0

    def reset(self):
        """Reset store"""
        self.id = None
        self.record_id = None
        self.name = None
        self.path = None
        self.file_id = None
        self.store_id = None
        self.thread_id = None
        self.uuid = None
        self.size = 0
        self.created = 0
        self.updated = 0

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "file_id": self.file_id,
            "store_id": self.store_id,
            "thread_id": self.thread_id,
            "uuid": self.uuid,
            "size": self.size,
            "created": self.created,
            "updated": self.updated,
        }

    def from_dict(self, data: dict):
        """
        Load from dictionary

        :param data: dictionary
        """
        self.id = data.get('id', None)
        self.name = data.get('name', None)
        self.path = data.get('path', None)
        self.file_id = data.get('file_id', None)
        self.store_id = data.get('store_id', None)
        self.thread_id = data.get('thread_id', None)
        self.uuid = data.get('uuid', None)
        self.size = data.get('size', 0)
        self.created = data.get('created', 0)
        self.updated = data.get('updated', 0)

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()
