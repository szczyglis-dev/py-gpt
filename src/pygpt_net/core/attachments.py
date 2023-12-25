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

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.provider.attachment.json_file import JsonFileProvider


class Attachments:
    def __init__(self, window=None):
        """
        Attachments

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.items = {}
        self.current = None

        # register data providers
        self.add_provider(JsonFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add data provider

        :param provider: data provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def install(self):
        """Install provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].install()
            except Exception as e:
                self.window.app.debug.log(e)

    def patch(self, app_version):
        """Patch provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].patch(app_version)
            except Exception as e:
                self.window.app.debug.log(e)

    def select(self, mode, id):
        """
        Select attachment by uuid

        :param mode: mode
        :param id: id
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            self.current = id

    def count(self, mode):
        """
        Count attachments

        :param mode: mode
        :return: attachments count
        :rtype: int
        """
        if mode not in self.items:
            self.items[mode] = {}

        return len(self.items[mode])

    def get_ids(self, mode):
        """
        Get items IDs

        :param mode: mode
        :return: items UUIDs
        :rtype: list
        """
        if mode not in self.items:
            self.items[mode] = {}

        return list(self.items[mode].keys())

    def get_id_by_idx(self, mode, idx):
        """
        Get ID by index

        :param mode: mode
        :param idx: index
        :return: file ID
        :rtype: str or None
        """
        i = 0
        for id in self.get_ids(mode):
            if i == idx:
                return id
            i += 1

    def get_by_id(self, mode, id):
        """
        Return attachment by ID

        :param mode: mode
        :param id: file id
        :return: dict
        :rtype: dict
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            return self.items[mode][id]

    def get_by_idx(self, mode, index):
        """
        Return item by index

        :param mode: mode
        :param index: item index
        :return: context item
        :rtype: dict
        """
        id = self.get_id_by_idx(mode, index)
        if id is not None:
            return self.items[mode][id]

    def get_all(self, mode):
        """
        Return all items in mode

        :param mode: mode
        :return: attachments items
        :rtype: dict
        """
        if mode not in self.items:
            self.items[mode] = {}

        return self.items[mode]

    def new(self, mode, name=None, path=None, auto_save=True):
        """
        Create new attachment

        :param mode: mode
        :param name: name
        :param path: path
        :param auto_save: auto_save
        :return: AttachmentItem
        :rtype: AttachmentsItem
        """
        attachment = self.create()
        attachment.name = name
        attachment.path = path

        if mode not in self.items:
            self.items[mode] = {}

        self.items[mode][attachment.id] = attachment
        self.current = attachment.id

        if auto_save:
            self.save()

        return attachment

    def build(self):
        """
        Build attachment

        :return: AttachmentItem
        :rtype: AttachmentItem
        """
        attachment = AttachmentItem()
        attachment.name = None
        attachment.path = None
        return attachment

    def create(self):
        """
        Create attachment item

        :return: AttachmentItem
        :rtype: AttachmentItem
        """
        attachment = self.build()
        if self.provider in self.providers:
            try:
                id = self.providers[self.provider].create(attachment)
                attachment.id = id
                return attachment
            except Exception as e:
                self.window.app.debug.log(e)

    def add(self, mode, item):
        """
        Add item to attachments

        :param mode: mode
        :param item: item to add
        """
        if mode not in self.items:
            self.items[mode] = {}

        id = item.id
        self.items[mode][id] = item  # add item to attachments

        # save attachments
        self.save()

    def has(self, mode):
        """
        Check id mode has attachments

        :param mode: mode
        :return: true if exists
        :rtype: bool
        """
        if mode not in self.items:
            self.items[mode] = {}

        return len(self.items[mode]) > 0

    def delete(self, mode, id):
        """
        Delete attachment by file_id

        :param mode: mode
        :param id: file id
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            del self.items[mode][id]
            self.save()

    def delete_all(self, mode):
        """
        Delete all attachments

        :param mode: mode
        """
        self.clear(mode)

        if self.provider in self.providers:
            try:
                self.providers[self.provider].truncate(mode)
            except Exception as e:
                self.window.app.debug.log(e)

    def clear(self, mode):
        """
        Clear all attachments in mode

        :param mode: mode
        """
        self.items[mode] = {}

    def clear_all(self):
        """
        Clear all attachments
        """
        self.items = {}

    def replace_id(self, mode, tmp_id, attachment):
        """
        Replace temporary id with real one

        :param mode: mode
        :param tmp_id: temporary id
        :param attachment: attachment
        """
        if mode not in self.items:
            self.items[mode] = {}

        if tmp_id in self.items[mode]:
            self.items[mode][attachment.id] = self.items[mode][tmp_id]
            del self.items[mode][tmp_id]
            self.save()

    def rename_file(self, mode, id, name):
        """
        Update name

        :param mode: mode
        :param id: file id
        :param name: new name
        """
        data = self.get_by_id(mode, id)
        data.name = name
        self.save()

    def from_files(self, mode, files):
        """
        Load attachments from assistant files

        :param mode: mode
        :param files: files
        """
        self.clear(mode)
        for id in files:
            file = files[id]
            item = AttachmentItem()
            item.name = id

            if 'name' in file and file['name'] is not None and file['name'] != "":
                item.name = file['name']
            if 'path' in file and file['path'] is not None and file['path'] != "":
                item.path = file['path']

            item.id = id
            item.remote = id
            item.send = True
            self.add(mode, item)

    def from_attachments(self, mode, attachments):
        """
        Load attachments from attachments

        :param mode: mode
        :param attachments: attachments
        """
        self.clear(mode)
        for id in attachments:
            attachment = attachments[id]
            self.add(mode, attachment)

    def load(self):
        """Load attachments"""
        if self.provider in self.providers:
            try:
                self.items = self.providers[self.provider].load()
            except Exception as e:
                self.window.app.debug.log(e)
                self.items = {}

    def save(self):
        """
        Save attachments
        """
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(self.items)
            except Exception as e:
                self.window.app.debug.log(e)
