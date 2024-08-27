#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 22:00:00                  #
# ================================================== #

import copy
import uuid

from packaging.version import Version
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.core.preset.json_file import JsonFileProvider


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

    def build(self) -> PresetItem:
        """
        Build empty preset

        :return: empty preset
        """
        preset = PresetItem()
        preset.uuid = str(uuid.uuid4())
        return preset

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
        curr_agent = self.build()
        curr_expert = self.build()

        # prepare ids
        id_chat = 'current.chat'
        id_completion = 'current.completion'
        id_img = 'current.img'
        id_vision = 'current.vision'
        id_langchain = 'current.langchain'
        id_assistant = 'current.assistant'
        id_llama = 'current.llama_index'
        id_agent = 'current.agent'
        id_expert = 'current.expert'

        # set default initial prompt for chat mode
        curr_chat.prompt = self.window.core.prompt.get('default')

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
        if id_agent in self.items:
            curr_agent = self.items[id_agent]
        if id_expert in self.items:
            curr_expert = self.items[id_expert]

        # allow usage in specific mode
        curr_chat.chat = True
        curr_completion.completion = True
        curr_img.img = True
        curr_vision.vision = True
        curr_langchain.langchain = True
        curr_assistant.assistant = True
        curr_llama.llama_index = True
        curr_agent.agent = True
        curr_expert.expert = True

        # always apply default name
        curr_chat.name = '*'
        curr_completion.name = '*'
        curr_img.name = '*'
        curr_vision.name = '*'
        curr_langchain.name = '*'
        curr_assistant.name = '*'
        curr_llama.name = '*'
        curr_agent.name = '*'
        curr_expert.name = '*'

        # append at first position
        self.items = {
            id_chat: curr_chat,
            id_completion: curr_completion,
            id_img: curr_img,
            id_vision: curr_vision,
            id_langchain: curr_langchain,
            id_assistant: curr_assistant,
            id_llama: curr_llama,
            id_agent: curr_agent,
            id_expert: curr_expert,
            **self.items
        }

    def exists(self, id: str) -> bool:
        """
        Check if preset exists

        :param id: preset id
        :return: True if exists
        """
        if id in self.items:
            return True
        return False

    def exists_uuid(self, uuid: str) -> bool:
        """
        Check if preset exists

        :param uuid: preset uuid
        :return: True if exists
        """
        for id in self.items:
            if self.items[id].uuid == uuid:
                return True
        return False

    def enable(self, id: str):
        """
        Enable preset

        :param id: preset id
        """
        if id in self.items:
            self.items[id].enabled = True
    def disable(self, id: str):
        """
        Disable preset

        :param id: preset id
        """
        if id in self.items:
            self.items[id].enabled = False

    def get_first_mode(self, id: str) -> str or None:
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
        if preset.agent:
            return 'agent'
        if preset.expert:
            return 'expert'
        return None

    def has(self, mode: str, id: str) -> bool:
        """
        Check if preset for mode exists

        :param mode: mode name
        :param id : preset id
        :return: True if exists
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

    def get_by_id(self, mode: str, id: str) -> PresetItem or None:
        """
        Return preset by id

        :param mode: mode name
        :param id: preset id
        :return: preset item
        """
        presets = self.get_by_mode(mode)
        if id in presets:
            return presets[id]
        return None

    def get_by_uuid(self, uuid: str) -> PresetItem or None:
        """
        Return preset by UUID

        :param uuid: preset UUID
        :return: preset item
        """
        for id in self.items:
            if self.items[id].uuid == uuid:
                return self.items[id]
        return None

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
                    or (mode == 'llama_index' and self.items[id].llama_index) \
                    or (mode == 'agent' and self.items[id].agent) \
                    or (mode == 'expert' and self.items[id].expert):
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
        new_id = id
        new_name = old_name
        while True:
            new_id = new_id + '_copy'
            new_name = new_name + ' copy'
            if new_id not in self.items:
                return new_id, new_name

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
        self.items[id].filename = id
        self.items[id].uuid = str(uuid.uuid4())  # generate new uuid
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
        self.items = dict(
            sorted(
                self.items.items(),
                key=lambda item: item[1].name
            )
        )

    def get_all(self) -> dict:
        """
        Return all presets

        :return: presets dict
        """
        return self.items

    def restore(self, mode: str):
        """
        Restore default preset for mode

        :param mode: mode name
        """
        base = self.load_base()
        id = "current." + mode
        if id in base:
            self.items[id] = base[id]
            self.save(id)

    def load_base(self):
        """Load base presets"""
        return self.provider.load_base()

    def load(self):
        """Load presets templates"""
        self.items = self.provider.load()
        self.patch_empty()  # patch empty UUIDs and filenames
        self.patch_duplicated()  # patch duplicated UUIDs

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

    def add_expert(self, agent_uuid: str, expert_uuid: str):
        """
        Add expert to agent

        :param agent_uuid: agent uuid
        :param expert_uuid: expert uuid
        """
        agent = self.get_by_uuid(agent_uuid)
        if agent is None:
            return
        if expert_uuid not in agent.experts:
            agent.experts.append(expert_uuid)
        self.save(agent.filename)

    def remove_expert(self, agent_uuid: str, expert_uuid: str):
        """
        Remove expert from agent
        :param agent_uuid: agent uuid
        :param expert_uuid: expert uuid
        """
        agent = self.get_by_uuid(agent_uuid)
        if agent is None:
            return
        if expert_uuid in agent.experts:
            agent.experts.remove(expert_uuid)
        self.save(agent.filename)

    def patch_empty(self):
        """Patch UUIDs for all presets"""
        patched = False
        for id in self.items:
            if self.items[id].uuid is None:
                self.items[id].uuid = str(uuid.uuid4())
                patched = True
            if self.items[id].filename is None or self.items[id].filename == "":
                self.items[id].filename = id
                patched = True
        if patched:
            self.save_all()

    def patch_duplicated(self):
        """Patch UUIDs for all presets"""
        patched = False
        uuids = []
        for id in self.items:
            if self.items[id].uuid in uuids:
                self.items[id].uuid = str(uuid.uuid4())
                patched = True
            uuids.append(self.items[id].uuid)
        if patched:
            self.save_all()