#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #
import datetime
import json
import os
import uuid

from .base import BaseProvider
from ...item.notepad import NotepadItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "notepad"
        self.config_file = 'notepad.json'

    def create_id(self):
        """
        Create unique uuid

        :return: uuid
        :rtype: str
        """
        return str(uuid.uuid4())

    def create(self, notepad):
        """
        Create new and return its ID

        :param notepad: NotepadItem
        :return: notepad ID
        :rtype: str
        """
        if notepad.id is None or notepad.id == "":
            notepad.id = self.create_id()
        return notepad.id

    def load_all(self):
        """Load notepads from file"""
        path = os.path.join(self.window.app.config.path, self.config_file)
        items = {}
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None:
                        return {}

                    # migrate from old version < 2.0.49
                    if 'items' not in data and 'content' in data:
                        ary = {}
                        for id in data['content']:
                            new_id = int(id)
                            notepad = NotepadItem()
                            notepad.id = new_id
                            notepad.title = "Notepad " + str(new_id)
                            notepad.content = data['content'][id]
                            notepad.created_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            notepad.updated_at = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            ary[new_id] = notepad
                        self.save_all(ary)
                        print("Migrated notepads from old version.")
                        return ary

                    # deserialize
                    if 'items' in data:
                        for id in data['items']:
                            item = data['items'][id]
                            notepad = NotepadItem()
                            self.deserialize(item, notepad)
                            id = notepad.id
                            items[id] = notepad
        except Exception as e:
            self.window.app.errors.log(e)
            items = {}

        return items

    def load(self, id):
        """Load notepad from file"""
        path = os.path.join(self.window.app.config.path, self.config_file)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return {}

                    # deserialize
                    for item in data['items']:
                        tmp_id = item['id']
                        if tmp_id == id:
                            notepad = NotepadItem()
                            self.deserialize(item, notepad)
                            return notepad
        except Exception as e:
            self.window.app.errors.log(e)

    def save(self, notepad):
        """
        Save notepad to file
        """
        try:
            id = notepad.id
            items = self.load_all()  # load all notepads
            items[id] = notepad  # update only current notepad
            self.save_all(items)

        except Exception as e:
            self.window.app.errors.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def save_all(self, items):
        """
        Save notepad to file
        """
        try:
            # update notepads
            path = os.path.join(self.window.app.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in items:
                notepad = items[id]
                ary[id] = self.serialize(notepad)

            data['__meta__'] = self.window.app.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.app.errors.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def remove(self, id):
        """
        Delete by id

        :param id: id
        """
        items = self.load_all()
        if id in items:
            del items[id]
            self.save_all(items)

    def truncate(self):
        """Delete all"""
        path = os.path.join(self.window.app.config.path, self.config_file)
        data = {'__meta__': self.window.app.config.append_meta(), 'items': {}}
        try:
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.app.errors.log(e)

    def patch(self, version):
        """
        Migrate presets to current app version

        :param version: current app version
        :return: true if migrated
        :rtype: bool
        """
        return False

    @staticmethod
    def serialize(notepad):
        """
        Serialize item to dict

        :return: serialized item
        :rtype: dict
        """
        return {
            'id': notepad.id,
            'title': notepad.title,
            'content': notepad.content,
            'created_at': notepad.created_at,  # '2019-01-01T00:00:00
            'updated_at': notepad.updated_at,  # '2019-01-01T00:00:00
        }

    @staticmethod
    def deserialize(data, notepad):
        """
        Deserialize item from dict

        :param data: serialized item
        :param notepad: NotepadItem
        """
        if 'id' in data:
            notepad.id = data['id']
        if 'title' in data:
            notepad.title = data['title']
        if 'content' in data:
            notepad.content = data['content']
        if 'created_at' in data:
            notepad.created_at = data['created_at']
        if 'updated_at' in data:
            notepad.updated_at = data['updated_at']

    def dump(self, item):
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
