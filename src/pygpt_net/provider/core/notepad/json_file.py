#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import datetime
import json
import os
import uuid

from packaging.version import Version

from pygpt_net.provider.core.notepad.base import BaseProvider
from pygpt_net.item.notepad import NotepadItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "notepad"
        self.config_file = 'notepad.json'

    def create_id(self) -> str:
        """
        Create unique uuid (in json file provider it is just uuid4)

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, notepad: NotepadItem) -> str:
        """
        Create new and return its ID

        :param notepad: NotepadItem
        :return: notepad ID
        """
        if notepad.id is None or notepad.id == "":
            notepad.id = self.create_id()
        return notepad.id

    def load_all(self) -> dict:
        """
        Load notepads from file

        :return: dict of NotepadItem
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
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
            self.window.core.debug.log(e)
            items = {}

        return items

    def load(self, id: str) -> NotepadItem | None:
        """
        Load notepad from file

        :param id: notepad ID
        :return: NotepadItem
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    if data == "" or data is None or 'items' not in data:
                        return None

                    # deserialize
                    for item in data['items']:
                        tmp_id = item['id']
                        if tmp_id == id:
                            notepad = NotepadItem()
                            self.deserialize(item, notepad)
                            return notepad
        except Exception as e:
            self.window.core.debug.log(e)

    def save(self, notepad: NotepadItem):
        """
        Save notepad to file

        :param notepad: NotepadItem
        """
        try:
            id = notepad.id
            items = self.load_all()  # load all notepads
            items[id] = notepad  # update only current notepad
            self.save_all(items)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def save_all(self, items: dict):
        """
        Save notepad to file

        :param items: dict of NotepadItem
        """
        try:
            # update notepads
            path = os.path.join(self.window.core.config.path, self.config_file)
            data = {}
            ary = {}

            # serialize
            for id in items:
                notepad = items[id]
                ary[id] = self.serialize(notepad)

            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = ary
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)

        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving notepad: {}".format(str(e)))

    def remove(self, id: str):
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
        path = os.path.join(self.window.core.config.path, self.config_file)
        data = {'__meta__': self.window.core.config.append_meta(), 'items': {}}
        try:
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.core.debug.log(e)

    def patch(self, version: Version) -> bool:
        """
        Migrate presets to current app version

        :param version: current app version
        :return: True if migrated
        """
        return False

    @staticmethod
    def serialize(notepad: NotepadItem) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': notepad.id,
            'title': notepad.title,
            'content': notepad.content,
            'created_at': notepad.created,  # '2019-01-01T00:00:00
            'updated_at': notepad.updated,  # '2019-01-01T00:00:00
        }

    @staticmethod
    def deserialize(data: dict, notepad: NotepadItem):
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
            notepad.created = data['created_at']
        if 'updated_at' in data:
            notepad.updated = data['updated_at']

    def dump(self, item: NotepadItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
