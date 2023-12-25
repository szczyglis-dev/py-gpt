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

import json
import os
import shutil
from packaging.version import parse as parse_version

from .base import BaseProvider
from ...item.preset import PresetItem


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.id = "json_file"
        self.type = "preset"
        self.config_dir = 'presets'

    def install(self):
        """
        Install provider data
        """
        # install presets
        presets_dir = os.path.join(self.window.app.config.path, self.config_dir)
        if not os.path.exists(presets_dir):
            src = os.path.join(self.window.app.config.get_root_path(), 'data', 'config', self.config_dir)
            shutil.copytree(src, presets_dir)
        else:
            # copy missing presets
            src = os.path.join(self.window.app.config.get_root_path(), 'data', 'config', self.config_dir)
            for file in os.listdir(src):
                src_file = os.path.join(src, file)
                dst_file = os.path.join(presets_dir, file)
                if not os.path.exists(dst_file):
                    shutil.copyfile(src_file, dst_file)

    def load(self):
        """
        Load presets from JSON file
        """
        items = {}
        path = os.path.join(self.window.app.config.path, self.config_dir)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    path = os.path.join(self.window.app.config.path, self.config_dir, filename)
                    with open(path, 'r', encoding="utf-8") as f:
                        preset = PresetItem()
                        self.deserialize(json.load(f), preset)
                        items[filename[:-5]] = preset
        except Exception as e:
            self.window.app.debug.log(e)

        return items

    def save(self, id, item):
        """
        Save preset to JSON file

        :param item: PresetItem
        """
        path = os.path.join(self.window.app.config.path, self.config_dir, id + '.json')
        data = self.serialize(item)
        data['__meta__'] = self.window.app.config.append_meta()
        dump = json.dumps(data, indent=4)
        try:
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.app.debug.log(e)

    def save_all(self, items):
        """
        Save all presets to JSON files

        :param items: items dict
        """
        for id in items:
            path = os.path.join(self.window.app.config.path, self.config_dir, id + '.json')

            # serialize
            data = self.serialize(items[id])
            data['__meta__'] = self.window.app.config.append_meta()
            dump = json.dumps(data, indent=4)
            try:
                with open(path, 'w', encoding="utf-8") as f:
                    f.write(dump)
            except Exception as e:
                self.window.app.debug.log(e)

    def remove(self, id):
        """
        Remove preset

        :param id: preset id
        """
        path = os.path.join(self.window.app.config.path, self.config_dir, id + '.json')
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.window.app.debug.log(e)

    def truncate(self):
        pass

    def patch(self, version):
        """
        Migrate presets to current app version

        :param version: current app version
        :return: true if migrated
        :rtype: bool
        """
        migrated = False
        for k in self.window.app.presets.items:
            data = self.window.app.presets.items[k]
            updated = False

            # get version of preset
            old = parse_version(data.version)

            # check if presets file is older than current app version
            if old < version:
                # < 2.0.0
                if old < parse_version("2.0.0"):
                    print("Migrating presets dir from < 2.0.0...")
                    self.window.app.updater.patch_file('presets', True)  # force replace file

                # < 2.0.53
                if old < parse_version("2.0.53") and k == 'current.assistant':
                    print("Migrating preset file from < 2.0.53...")
                    dst = os.path.join(self.window.app.config.path, 'presets', 'current.assistant.json')
                    src = os.path.join(self.window.app.config.get_root_path(), 'data', 'config', 'presets',
                                       'current.assistant.json')
                    shutil.copyfile(src, dst)
                    updated = True
                    print("Patched file: {}.".format(dst))

            # update file
            if updated:
                self.window.app.presets.load()  # reload presets from patched files
                self.window.app.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated

    @staticmethod
    def serialize(item):
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        :rtype: dict
        """
        return {
            'name': item.name,
            'ai_name': item.ai_name,
            'user_name': item.user_name,
            'prompt': item.prompt,
            'chat': item.chat,
            'completion': item.completion,
            'img': item.img,
            'vision': item.vision,
            'langchain': item.langchain,
            'assistant': item.assistant,
            'temperature': item.temperature,
            'filename': item.filename,
        }

    @staticmethod
    def deserialize(data, item):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if 'name' in data:
            item.name = data['name']
        if 'ai_name' in data:
            item.ai_name = data['ai_name']
        if 'user_name' in data:
            item.user_name = data['user_name']
        if 'prompt' in data:
            item.prompt = data['prompt']
        if 'chat' in data:
            item.chat = data['chat']
        if 'completion' in data:
            item.completion = data['completion']
        if 'img' in data:
            item.img = data['img']
        if 'vision' in data:
            item.vision = data['vision']
        if 'langchain' in data:
            item.langchain = data['langchain']
        if 'assistant' in data:
            item.assistant = data['assistant']
        if 'temperature' in data:
            item.temperature = data['temperature']
        if 'filename' in data:
            item.filename = data['filename']
        if '__meta__' in data and 'version' in data['__meta__']:
            item.version = data['__meta__']['version']

    def dump(self, item):
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        :rtype: str
        """
        return json.dumps(self.serialize(item))
