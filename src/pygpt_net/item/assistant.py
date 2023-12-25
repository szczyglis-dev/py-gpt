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

    def has_file(self, id):
        """
        Check if assistant has file with ID

        :param id: file ID
        :return: bool
        """
        return id in self.files

    def add_file(self, id):
        """
        Add empty file to assistant

        :param id: file ID
        """
        self.files[id] = {}
        self.files[id]['id'] = id

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

    def has_attachment(self, id):
        """
        Check if assistant has attachment with ID

        :param id: attachment ID
        :return: bool
        :rtype: bool
        """
        return id in self.attachments

    def add_attachment(self, attachment):
        """
        Add attachment to assistant

        :param attachment: attachment
        """
        id = attachment.id
        self.attachments[id] = attachment

    def delete_attachment(self, id):
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
