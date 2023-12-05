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
import uuid


class Attachments:
    def __init__(self, config=None):
        """
        Attachments

        :param config: config object
        """
        self.config = config
        self.config_file = 'attachments.json'
        self.items = {}
        self.current = None

    def create_id(self):
        """
        Creates unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def select(self, mode, file_id):
        """
        Select attachment by uuid

        :param mode: mode
        :param file_id: file_id
        """
        if mode not in self.items:
            self.items[mode] = {}

        if file_id in self.items[mode]:
            self.current = file_id

    def count(self, mode):
        """
        Counts attachments

        :param mode: mode
        :return: attachments count
        """
        if mode not in self.items:
            self.items[mode] = {}

        return len(self.items[mode])

    def get_ids(self, mode):
        """
        Gets items IDs

        :param mode: mode
        :return: items UUIDs
        """
        if mode not in self.items:
            self.items[mode] = {}

        return self.items[mode].keys()

    def get_id_by_idx(self, mode, idx):
        """
        Gets ID by index

        :param mode: mode
        :param idx: index
        :return: uuid
        """
        i = 0
        for file_id in self.get_ids(mode):
            if i == idx:
                return file_id
            i += 1

    def get_by_id(self, mode, file_id):
        """
        Returns attachment by ID

        :param mode: mode
        :param file_id: file_id
        :return: dict
        """
        if mode not in self.items:
            self.items[mode] = {}

        if file_id in self.items[mode]:
            return self.items[mode][file_id]

    def get_by_idx(self, mode, index):
        """
        Returns item by index

        :param mode: mode
        :param index: item index
        :return: context item
        """
        file_id = self.get_id_by_idx(mode, index)
        if file_id is not None:
            return self.items[mode][file_id]

    def get_all(self, mode):
        """
        Returns all items in mode

        :return: attachments items
        """
        if mode not in self.items:
            self.items[mode] = {}

        return self.items[mode]

    def delete(self, mode, file_id):
        """
        Deletes attachment by file_id

        :param mode: mode
        :param file_id: file_id
        """
        if mode not in self.items:
            self.items[mode] = {}

        if file_id in self.items[mode]:
            del self.items[mode][file_id]
            self.save()

    def delete_all(self, mode):
        """
        Deletes all attachments

        :param mode: mode
        """
        self.clear(mode)

        # update index
        path = os.path.join(self.config.path, self.config_file)
        data = {'__meta__': self.config.append_meta(), 'items': {}}
        try:
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()
        except Exception as e:
            print(e)

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

    def new(self, mode, name=None, path=None, auto_save=True):
        """
        Creates new attachment

        :param mode: mode
        :param name: name
        :param path: path
        :param auto_save: auto_save
        :return: created UUID
        """
        file_id = self.create_id()  # create unique id
        attachment = AttachmentItem()
        attachment.id = file_id
        attachment.name = name
        attachment.path = path

        if mode not in self.items:
            self.items[mode] = {}

        self.items[mode][file_id] = attachment
        self.current = file_id

        if auto_save:
            self.save()

        return file_id

    def add(self, mode, item):
        """
        Adds item to attachments

        :param mode: mode
        :param item: item to add
        """
        if mode not in self.items:
            self.items[mode] = {}

        file_id = item.id
        self.items[mode][file_id] = item  # add item to attachments

        # save to file
        self.save()

    def replace_id(self, mode, tmp_id, attachment):
        """
        Replaces temporary id with real one

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

    def rename_file(self, mode, file_id, name):
        """
        Updates name

        :param mode: mode
        :param file_id: file_id
        :param name: new name
        """
        data = self.get_by_id(mode, file_id)
        data.name = name
        self.save()

    def from_files(self, mode, files):
        """
        Loads attachments from assistant files

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

    def load(self):
        """Loads attachments from file"""
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
                    for mode in data['items']:
                        self.items[mode] = {}
                        for id in data['items'][mode]:
                            attachment = data['items'][mode][id]
                            item = AttachmentItem()
                            item.deserialize(attachment)
                            self.items[mode][id] = item
        except Exception as e:
            print(e)
            self.items = {}

    def save(self):
        """
        Saves attachments to file
        """
        try:
            # update attachments
            path = os.path.join(self.config.path, self.config_file)
            data = {}
            items = {}

            # serialize
            for mode in self.items:
                items[mode] = {}
                for id in self.items[mode]:
                    attachment = self.items[mode][id]
                    items[mode][id] = attachment.serialize()

            data['__meta__'] = self.config.append_meta()
            data['items'] = items
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

        except Exception as e:
            print("Error while saving attachments: {}".format(str(e)))


class AttachmentItem:
    def __init__(self):
        """
        Attachment item
        """
        self.name = None
        self.id = None
        self.path = None
        self.remote = None
        self.send = False

    def serialize(self):
        """
        Serializes item to dict

        :return: serialized item
        """
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'remote': self.remote,
            'send': self.send
        }

    def deserialize(self, data):
        """Deserializes item from dict"""
        if 'id' in data:
            self.id = data['id']
        if 'name' in data:
            self.name = data['name']
        if 'path' in data:
            self.path = data['path']
        if 'remote_id' in data:
            self.remote = data['remote']
        if 'send' in data:
            self.send = data['send']

    def dump(self):
        """Dumps item to string"""
        return json.dumps(self.serialize())
