#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

import json
import os
import shutil
from typing import Dict, Optional, Any

from packaging.version import Version

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)
from pygpt_net.provider.core.preset.base import BaseProvider
from pygpt_net.item.preset import PresetItem

from .patch import Patch


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "json_file"
        self.type = "preset"

    def install(self):
        """Install provider data"""
        # install presets
        presets_dir = self.window.core.config.get_user_dir('presets')
        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets')
        if not os.path.exists(presets_dir):
            shutil.copytree(src, presets_dir)
        else:
            # copy missing presets
            for file in os.listdir(src):
                src_file = os.path.join(src, file)
                dst_file = os.path.join(presets_dir, file)
                if not os.path.exists(dst_file):
                    shutil.copyfile(src_file, dst_file)

    def load(self) -> Optional[Dict[str, PresetItem]]:
        """
        Load presets from JSON files

        :return: dict or None
        """
        items = {}
        path = self.window.core.config.get_user_dir('presets')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    path = os.path.join(self.window.core.config.get_user_dir('presets'), filename)
                    with open(path, 'r', encoding="utf-8") as f:
                        preset = PresetItem()
                        self.deserialize(json.load(f), preset)
                        items[filename[:-5]] = preset
        except Exception as e:
            self.window.core.debug.log(e)

        return items

    def load_base(self) -> Optional[Dict[str, PresetItem]]:
        """
        Load base presets from JSON files

        :return: dict or None
        """
        items = {}
        path = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    path = os.path.join(
                        os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets'),
                        filename
                    )
                    with open(path, 'r', encoding="utf-8") as f:
                        preset = PresetItem()
                        self.deserialize(json.load(f), preset)
                        items[filename[:-5]] = preset
        except Exception as e:
            self.window.core.debug.log(e)

        return items

    def save(self, id: str, item: PresetItem):
        """
        Save preset to JSON file

        :param id: preset id
        :param item: PresetItem
        """
        path = os.path.join(self.window.core.config.get_user_dir('presets'), id + '.json')
        data = self.serialize(item)
        data['__meta__'] = self.window.core.config.append_meta()
        dump = json.dumps(data, indent=4)
        try:
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            self.window.core.debug.log(e)

    def save_all(self, items: Dict[str, PresetItem]):
        """
        Save all presets to JSON files

        :param items: items dict
        """
        for id in items:
            path = os.path.join(self.window.core.config.get_user_dir('presets'), id + '.json')

            # serialize
            data = self.serialize(items[id])
            data['__meta__'] = self.window.core.config.append_meta()
            dump = json.dumps(data, indent=4)
            try:
                with open(path, 'w', encoding="utf-8") as f:
                    f.write(dump)
            except Exception as e:
                self.window.core.debug.log(e)

    def remove(self, id: str):
        """
        Remove preset

        :param id: preset id
        """
        path = os.path.join(self.window.core.config.get_user_dir('presets'), id + '.json')
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                self.window.core.debug.log(e)

    def truncate(self):
        pass

    def patch(self, version: Version) -> bool:
        """
        Migrate presets to current app version

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)

    @staticmethod
    def serialize(item: PresetItem) -> Dict[str, Any]:
        """
        Serialize item to dict

        :param item: item to serialize
        :return: serialized item
        """
        return {
            'uuid': item.uuid,
            'name': item.name,
            'ai_name': item.ai_name,
            'user_name': item.user_name,
            'prompt': item.prompt,
            MODE_CHAT: item.chat,
            MODE_COMPLETION: item.completion,
            MODE_IMAGE: item.img,
            MODE_VISION: item.vision,
            # MODE_LANGCHAIN: item.langchain,
            MODE_ASSISTANT: item.assistant,
            MODE_LLAMA_INDEX: item.llama_index,
            MODE_AGENT: item.agent,
            MODE_AGENT_LLAMA: item.agent_llama,
            MODE_EXPERT: item.expert,
            MODE_AUDIO: item.audio,
            MODE_RESEARCH: item.research,
            'temperature': item.temperature,
            'filename': item.filename,
            'model': item.model,
            'tools': item.tools,
            'experts': item.experts,
            'idx': item.idx,
            'agent_provider': item.agent_provider,
            'assistant_id': item.assistant_id,
            'enabled': item.enabled,
        }

    @staticmethod
    def deserialize(data: Dict[str, Any], item: PresetItem):
        """
        Deserialize item from dict

        :param data: serialized item
        :param item: item to deserialize
        """
        if MODE_CHAT in data:
            item.chat = data[MODE_CHAT]
        if MODE_COMPLETION in data:
            item.completion = data[MODE_COMPLETION]
        if MODE_IMAGE in data:
            item.img = data[MODE_IMAGE]
        if MODE_VISION in data:
            item.vision = data[MODE_VISION]
        # if MODE_LANGCHAIN in data:
            # item.langchain = data[MODE_LANGCHAIN]
        if MODE_ASSISTANT in data:
            item.assistant = data[MODE_ASSISTANT]
        if MODE_LLAMA_INDEX in data:
            item.llama_index = data[MODE_LLAMA_INDEX]
        if MODE_AGENT in data:
            item.agent = data[MODE_AGENT]
        if MODE_AGENT_LLAMA in data:
            item.agent_llama = data[MODE_AGENT_LLAMA]
        if MODE_EXPERT in data:
            item.expert = data[MODE_EXPERT]
        if MODE_AUDIO in data:
            item.audio = data[MODE_AUDIO]
        if MODE_RESEARCH in data:
            item.research = data[MODE_RESEARCH]

        if 'uuid' in data:
            item.uuid = data['uuid']
        if 'name' in data:
            item.name = data['name']
        if 'ai_name' in data:
            item.ai_name = data['ai_name']
        if 'user_name' in data:
            item.user_name = data['user_name']
        if 'prompt' in data:
            item.prompt = data['prompt']
        if 'temperature' in data:
            item.temperature = data['temperature']
        if 'filename' in data:
            item.filename = data['filename']
        if 'model' in data:
            item.model = data['model']
        if 'tools' in data:
            item.tools = data['tools']
        if 'experts' in data:
            item.experts = data['experts']
        if 'idx' in data:
            item.idx = data['idx']
        if 'agent_provider' in data:
            item.agent_provider = data['agent_provider']
        if 'assistant_id' in data:
            item.assistant_id = data['assistant_id']
        if 'enabled' in data:
            item.enabled = data['enabled']

        # get version
        if '__meta__' in data and 'version' in data['__meta__']:
            item.version = data['__meta__']['version']

    def dump(self, item: PresetItem) -> str:
        """
        Dump to string

        :param item: item to dump
        :return: dumped item as string (json)
        """
        return json.dumps(self.serialize(item))
