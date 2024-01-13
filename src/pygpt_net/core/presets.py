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

import copy

from packaging.version import Version
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.preset.json_file import JsonFileProvider


class Presets:

    def __init__(self, window=None):
        """
        Presets core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def build(self):
        """
        Build empty preset

        :return: empty preset
        :rtype: PresetItem
        """
        return PresetItem()

    def append_current(self):
        """Append current presets"""
        # create empty presets
        curr_chat = self.build()
        curr_completion = self.build()
        curr_img = self.build()
        curr_vision = self.build()
        curr_langchain = self.build()
        curr_assistant = self.build()
        curr_llama = self.build()

        # prepare ids
        id_chat = 'current.chat'
        id_completion = 'current.completion'
        id_img = 'current.img'
        id_vision = 'current.vision'
        id_langchain = 'current.langchain'
        id_assistant = 'current.assistant'
        id_llama = 'current.llama_index'

        # set default initial prompt for chat mode
        curr_chat.prompt = self.window.core.config.get('default_prompt')

        # get data from presets if exists
        if id_chat in self.items:
            curr_chat = self.items[id_chat]
        if id_completion in self.items:
            curr_completion = self.items[id_completion]
        if id_img in self.items:
            curr_img = self.items[id_img]
        if id_vision in self.items:
            curr_vision = self.items[id_vision]
        if id_langchain in self.items:
            curr_langchain = self.items[id_langchain]
        if id_assistant in self.items:
            curr_assistant = self.items[id_assistant]
        if id_llama in self.items:
            curr_llama = self.items[id_llama]

        # allow usage in specific mode
        curr_chat.chat = True
        curr_completion.completion = True
        curr_img.img = True
        curr_vision.vision = True
        curr_langchain.langchain = True
        curr_assistant.assistant = True
        curr_llama.llama_index = True

        # always apply default name
        curr_chat.name = '*'
        curr_completion.name = '*'
        curr_img.name = '*'
        curr_vision.name = '*'
        curr_langchain.name = '*'
        curr_assistant.name = '*'
        curr_llama.name = '*'

        # append at first position
        self.items = {
            id_chat: curr_chat,
            id_completion: curr_completion,
            id_img: curr_img,
            id_vision: curr_vision,
            id_langchain: curr_langchain,
            id_assistant: curr_assistant,
            id_llama: curr_llama,
            **self.items
        }

    def exists(self, id: str) -> bool:
        """
        Check if preset exists

        :param id: preset id
        :return: bool
        """
        if id in self.items:
            return True
        return False

    def get_first_mode(self, id: str) -> str:
        """
        Return first mode for preset

        :param id: preset id
        :return: mode name
        """
        preset = self.items[id]
        if preset.chat:
            return 'chat'
        if preset.completion:
            return 'completion'
        if preset.img:
            return 'img'
        if preset.vision:
            return 'vision'
        if preset.langchain:
            return 'langchain'
        if preset.assistant:
            return 'assistant'
        if preset.llama_index:
            return 'llama_index'
        return None

    def has(self, mode: str, id: str) -> bool:
        """
        Check if preset for mode exists

        :param mode: mode name
        :param name: preset id
        :return: bool
        """
        presets = self.get_by_mode(mode)
        if id in presets:
            return True
        return False

    def get_by_idx(self, idx: int, mode: str) -> str:
        """
        Return preset by index

        :param idx: index
        :param mode: mode
        :return: preset id
        """
        presets = self.get_by_mode(mode)
        return list(presets.keys())[idx]

    def get_by_mode(self, mode: str) -> dict:
        """
        Return presets for mode

        :param mode: mode name
        :return: presets dict for mode
        """
        presets = {}
        for id in self.items:
            if (mode == 'chat' and self.items[id].chat) \
                    or (mode == 'completion' and self.items[id].completion) \
                    or (mode == 'img' and self.items[id].img) \
                    or (mode == 'vision' and self.items[id].vision) \
                    or (mode == 'langchain' and self.items[id].langchain) \
                    or (mode == 'assistant' and self.items[id].assistant) \
                    or (mode == 'llama_index' and self.items[id].llama_index):
                presets[id] = self.items[id]
        return presets

    def get_idx_by_id(self, mode: str, id: str) -> int:
        """
        Return preset index

        :param mode: mode name
        :param id: preset id
        :return: preset idx
        """
        presets = self.get_by_mode(mode)
        i = 0
        for key in presets:
            if key == id:
                return i
            i += 1
        return 0

    def get_default(self, mode: str) -> str or None:
        """
        Return default preset for mode

        :param mode: mode name
        :return: default prompt name
        """
        presets = self.get_by_mode(mode)
        if len(presets) == 0:
            return None
        return list(presets.keys())[0]

    def get_duplicate_name(self, id: str) -> (str, str):
        """
        Prepare name for duplicated preset

        :param id: preset id
        :return: new ID, new name
        """
        old_name = self.items[id].name
        i = 1
        while True:
            new_id = id + '_' + str(i)
            if new_id not in self.items:
                return new_id, old_name + ' (' + str(i) + ')'
            i += 1

    def duplicate(self, id: str) -> str:
        """
        Make preset duplicate

        :param id: preset id
        :return: duplicated preset ID
        """
        prev_id = id
        id, name = self.get_duplicate_name(id)
        self.items[id] = copy.deepcopy(self.items[prev_id])
        self.items[id].name = name
        self.sort_by_name()
        return id

    def remove(self, id: str, remove_file: bool = True):
        """
        Delete preset

        :param id: preset id
        :param remove_file: also remove preset JSON config file
        """
        if id in self.items:
            self.items.pop(id)

        if remove_file:
            self.provider.remove(id)
            # self.load_presets()

    def sort_by_name(self):
        """
        Sort presets by name
        """
        self.items = dict(sorted(self.items.items(), key=lambda item: item[1].name))

    def get_all(self) -> dict:
        """
        Return all presets

        :return: presets dict
        """
        return self.items

    def load(self):
        """Load presets templates"""
        self.items = self.provider.load()

        # sort presets
        self.sort_by_name()
        self.append_current()

    def save(self, id: str):
        """
        Save preset

        :param id: preset id
        """
        if id not in self.items:
            return

        self.provider.save(id, self.items[id])

    def save_all(self):
        """Save all presets"""
        self.provider.save_all(self.items)
