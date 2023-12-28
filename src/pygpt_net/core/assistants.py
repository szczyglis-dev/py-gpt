#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 17:00:00                  #
# ================================================== #

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.provider.assistant.json_file import JsonFileProvider


class Assistants:
    def __init__(self, window=None):
        """
        Assistants

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)  # json file provider
        self.current_file = None
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version):
        """Patch provider data"""
        self.provider.patch(app_version)

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
        Create new assistant item (only empty object)

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
        :param attachment: attachment object
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
        if idx >= len(files):
            return None
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
        if id not in files:
            return None
        return files[id]

    def import_files(self, assistant, data, import_data=True):
        """
        Import files from remote API

        :param assistant: assistant object
        :param data: data from remote API
        :param import_data: import data from remote API
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

            # if file with this ID already in assistant.files
            if id in assistant.files:
                if 'name' in assistant.files[id] and assistant.files[id]['name'] != '':
                    name = assistant.files[id]['name']
                else:
                    name = id
                    # import name from remote
                    if import_data:
                        name = self.import_filenames(id)
                if 'path' in assistant.files[id]:
                    path = assistant.files[id]['path']
            elif id in assistant.attachments:
                name = assistant.attachments[id].name
                path = assistant.attachments[id].path
            else:
                name = id
                if import_data:
                    name = self.import_filenames(id)
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

    def import_filenames(self, id):
        """
        Import filenames from remote API

        :param id: file id
        :return: filename
        :rtype: str
        """
        name = id
        try:
            remote_data = self.window.core.gpt.assistants.file_info(id)
            if remote_data is not None:
                name = remote_data.filename
        except Exception as e:
            self.window.core.debug.log(e)
        return name

    def load(self):
        """Load assistants"""
        self.items = self.provider.load()

    def save(self):
        """Save assistants"""
        self.provider.save(self.items)
