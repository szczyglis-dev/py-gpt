#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 15:00:00                  #
# ================================================== #

import json

from pygpt_net.item.attachment import AttachmentItem


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
        self.files = {}  # file IDs (files uploaded to remote storage)
        self.attachments = {}  # local attachments
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

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "model": self.model,
            "meta": self.meta,
            "files": self.files,
            "attachments": self.attachments,
            "tool.code_interpreter": self.tools["code_interpreter"],
            "tool.retrieval": self.tools["retrieval"],
            "tool.function": self.tools["function"],
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

        :return: bool
        """
        return len(self.tools['function']) > 0

    def get_functions(self) -> list:
        """
        Return assistant functions

        :return: functions
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
        """
        Clear files
        """
        self.files = {}

    def has_attachment(self, id: str) -> bool:
        """
        Check if assistant has attachment with ID

        :param id: attachment ID
        :return: bool
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
        """
        Clear attachments
        """
        self.attachments = {}

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()
