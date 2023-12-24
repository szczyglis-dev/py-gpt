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

import copy

from .item.preset import PresetItem
from .provider.preset.json_file import JsonFileProvider


class Presets:

    def __init__(self, window=None):
        """
        Presets

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.items = {}

        # register data providers
        self.add_provider(JsonFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add data provider

        :param provider: data provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].window = self.window

    def save(self, id):
        """
        Save preset

        :param id: preset id
        """
        if id not in self.items:
            return

        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(id, self.items[id])
            except Exception as e:
                self.window.app.errors.log(e)

    def sort_by_name(self):
        """Sort presets by name"""
        pass  # TODO

    def load(self):
        """Load presets templates"""
        if self.provider in self.providers:
            try:
                self.items = self.providers[self.provider].load()
            except Exception as e:
                self.window.app.errors.log(e)
                self.items = {}

        # sort presets
        self.sort_by_name()
        self.append_current()

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

        # prepare ids
        id_chat = 'current.chat'
        id_completion = 'current.completion'
        id_img = 'current.img'
        id_vision = 'current.vision'
        id_langchain = 'current.langchain'
        id_assistant = 'current.assistant'

        # set default initial prompt for chat mode
        curr_chat.prompt = self.window.app.config.get('default_prompt')

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

        # allow usage in specific mode
        curr_chat.chat = True
        curr_completion.completion = True
        curr_img.img = True
        curr_vision.vision = True
        curr_langchain.langchain = True
        curr_assistant.assistant = True

        # always apply default name
        curr_chat.name = '*'
        curr_completion.name = '*'
        curr_img.name = '*'
        curr_vision.name = '*'
        curr_langchain.name = '*'
        curr_assistant.name = '*'

        # append at first position
        self.items = {
            id_chat: curr_chat,
            id_completion: curr_completion,
            id_img: curr_img,
            id_vision: curr_vision,
            id_langchain: curr_langchain,
            id_assistant: curr_assistant,
            **self.items
        }

    def get_by_idx(self, idx, mode):
        """
        Return preset by index

        :param idx: index
        :param mode: mode
        :return: preset id
        :rtype: str
        """
        presets = self.get_by_mode(mode)
        return list(presets.keys())[idx]

    def has(self, mode, id):
        """
        Check if preset for mode exists

        :param mode: mode name
        :param name: preset id
        :return: bool
        :rtype: bool
        """
        presets = self.get_by_mode(mode)
        if id in presets:
            return True
        return False

    def get_by_mode(self, mode):
        """
        Return presets for mode

        :param mode: mode name
        :return: presets dict for mode
        :rtype: dict
        """
        presets = {}
        for id in self.items:
            if (mode == 'chat' and self.items[id].chat) \
                    or (mode == 'completion' and self.items[id].completion) \
                    or (mode == 'img' and self.items[id].img) \
                    or (mode == 'vision' and self.items[id].vision) \
                    or (mode == 'langchain' and self.items[id].langchain) \
                    or (mode == 'assistant' and self.items[id].assistant):
                presets[id] = self.items[id]
        return presets

    def get_idx_by_id(self, mode, id):
        """
        Return preset index

        :param mode: mode name
        :param id: preset id
        :return: preset idx
        :rtype: int
        """
        presets = self.get_by_mode(mode)
        i = 0
        for key in presets:
            if key == id:
                return i
            i += 1
        return 0

    def remove(self, id, remove_file=True):
        """
        Delete preset

        :param id: preset id
        :param remove_file: also remove preset JSON config file
        """
        if id in self.items:
            self.items.pop(id)

        if remove_file:
            if self.provider in self.providers:
                try:
                    self.providers[self.provider].remove(id)
                except Exception as e:
                    self.window.app.errors.log(e)
            # self.load_presets()

    def get_default(self, mode):
        """
        Return default preset for mode

        :param mode: mode name
        :return: default prompt name
        :rtype: str
        """
        presets = self.get_by_mode(mode)
        if len(presets) == 0:
            return None
        return list(presets.keys())[0]

    def get_duplicate_name(self, id):
        """
        Prepare name for duplicated preset

        :param id: preset id
        :return: new ID, new name
        :rtype: (str, str)
        """
        old_name = self.items[id].name
        i = 1
        while True:
            new_id = id + '_' + str(i)
            if new_id not in self.items:
                return new_id, old_name + ' (' + str(i) + ')'
            i += 1

    def duplicate(self, id):
        """
        Make preset duplicate

        :param id: preset id
        :return: duplicated preset ID
        :rtype: str
        """
        prev_id = id
        id, name = self.get_duplicate_name(id)
        self.items[id] = copy.deepcopy(self.items[prev_id])
        self.items[id].name = name
        self.sort_by_name()
        return id

    def save_all(self):
        """Save all presets"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save_all(self.items)
            except Exception as e:
                self.window.app.errors.log(e)
