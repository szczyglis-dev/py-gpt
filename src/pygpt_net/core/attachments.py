#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.03 15:00:00                  #
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

    def select(self, uuid):
        """
        Select attachment by uuid

        :param uuid: uuid
        """
        if uuid in self.items:
            self.current = uuid

    def count(self):
        """
        Counts attachments

        :return: attachments count
        """
        return len(self.items)

    def exists_by_uuid(self, uuid):
        """
        Checks if attachment exists

        :param uuid: uuid
        :return: bool
        """
        return uuid in self.items

    def exists_by_path(self, path):
        """
        Checks if attachment exists

        :param path: path
        :return: bool
        """
        for uuid in self.items:
            if self.items[uuid].path == path:
                return True
        return False

    def get_ids(self):
        """
        Gets items

        :return: items UUIDs
        """
        return self.items.keys()

    def get_uuid_by_idx(self, idx):
        """
        Gets UUID by index

        :param idx: index
        :return: uuid
        """
        i = 0
        for uuid in self.get_ids():
            if i == idx:
                return uuid
            i += 1

    def get_by_uuid(self, uuid):
        """
        Returns attachment by uuid

        :param uuid: uuid
        :return: dict
        """
        if uuid in self.items:
            return self.items[uuid]

    def get_by_idx(self, index):
        """
        Returns item by index

        :param index: item index
        :return: context item
        """
        uuid = self.get_uuid_by_idx(index)
        if uuid is not None:
            return self.items[uuid]

    def get_all(self):
        """
        Returns all items

        :return: attachments items
        """
        return self.items

    def delete(self, uuid):
        """
        Deletes attachment by uuid

        :param uuid: uuid
        """
        if uuid in self.items:
            del self.items[uuid]
            self.save()

    def delete_all(self):
        """Deletes all attachments"""
        self.clear()

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

    def clear(self):
        """Clear all attachments"""
        self.items = {}

    def new(self, name=None, path=None, auto_save=True):
        """
        Creates new attachment

        :return: created UUID
        """
        uuid = self.create_id()  # create unique id
        attachment = AttachmentItem()
        attachment.id = uuid
        attachment.name = name
        attachment.path = path

        self.items[uuid] = attachment
        self.current = uuid

        if auto_save:
            self.save()

        return uuid

    def add(self, item):
        """
        Adds item to attachments

        :param item: item to add
        """
        uuid = item.uuid
        self.items[uuid] = item  # add item to attachments

        # save to file
        self.save()

    def replace_id(self, tmp_id, attachment):
        """
        Replaces temporary id with real one

        :param tmp_id: temporary id
        :param attachment: attachment
        """
        if tmp_id in self.items:
            self.items[attachment.uuid] = self.items[tmp_id]
            del self.items[tmp_id]
            self.save()

    def rename_file(self, file_id, name):
        """
        Updates name

        :param file_id: file_id
        :param name: new name
        """
        data = self.get_by_uuid(file_id)
        data.name = name
        self.save()

    def from_files(self, files):
        """
        Loads attachments from assistant files

        :param files: files
        """
        self.clear()
        for id in files:
            file = files[id]
            item = AttachmentItem()
            item.name = id
            if 'name' in file and file['name'] is not None and file['name'] != "":
                item.name = file['name']
            if 'path' in file and file['path'] is not None and file['path'] != "":
                item.path = file['path']
            item.uuid = id
            item.remote = id
            item.send = True
            self.add(item)

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
                    for id in data['items']:
                        attachment = data['items'][id]
                        item = AttachmentItem()
                        item.deserialize(attachment)
                        self.items[id] = item
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
            for uuid in self.items:
                attachment = self.items[uuid]
                items[uuid] = attachment.serialize()

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
        self.uuid = None
        self.path = None
        self.remote = None
        self.send = False

    def serialize(self):
        """
        Serializes item to dict

        :return: serialized item
        """
        return {
            'name': self.name,
            'uuid': self.uuid,
            'path': self.path,
            'remote': self.remote,
            'send': self.send
        }

    def deserialize(self, data):
        """Deserializes item from dict"""
        if 'name' in data:
            self.name = data['name']
        if 'uuid' in data:
            self.uuid = data['uuid']
        if 'path' in data:
            self.path = data['path']
        if 'remote_id' in data:
            self.remote = data['remote']
        if 'send' in data:
            self.send = data['send']

    def dump(self):
        """Dumps item to string"""
        return json.dumps(self.serialize())
