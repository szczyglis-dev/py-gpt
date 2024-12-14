#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Optional, Dict

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.provider.core.assistant.json_file import JsonFileProvider

from .files import Files
from .store import Store


class Assistants:
    def __init__(self, window=None):
        """
        Assistants core

        :param window: Window instance
        """
        self.window = window
        self.files = Files(window)
        self.store = Store(window)
        self.provider = JsonFileProvider(window)  # json file provider
        self.current_file = None
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()
        self.files.install()
        self.store.install()

    def patch(self, app_version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        res1 = self.provider.patch(app_version)
        res2 = self.store.patch(app_version)
        return res1 or res2

    def get_by_idx(self, idx: int) -> str:
        """
        Return assistant ID by index

        :param idx: index
        :return: assistant ID
        """
        assistants = self.get_all()
        return list(assistants.keys())[idx]

    def get_by_id(self, id: str) -> Optional[AssistantItem]:
        """
        Return assistant by ID

        :param id: ID
        :return: assistant
        """
        assistants = self.get_all()
        if id not in assistants:
            return None
        return assistants[id]

    def get_all(self) -> Dict[str, AssistantItem]:
        """
        Return assistants

        :return: assistants dict
        """
        return self.items

    def has(self, id: str) -> bool:
        """
        Check if assistant exists

        :param id: assistant ID
        :return: bool
        """
        return id in self.items

    def create(self) -> AssistantItem:
        """
        Create new assistant item (only empty object)

        :return: assistant ID
        """
        assistant = AssistantItem()
        return assistant

    def add(self, assistant: AssistantItem):
        """
        Add assistant

        :param assistant: item to add
        """
        id = assistant.id
        self.items[id] = assistant  # add assistant

        # save to file
        self.save()

    def delete(self, id: str):
        """
        Delete assistant

        :param id: id of assistant
        """
        if id in self.items:
            self.items.pop(id)
        self.save()

    def clear(self):
        """Clear all assistants"""
        self.items = {}
        self.save()

    def replace_attachment(
            self,
            assistant: AssistantItem,
            attachment: AttachmentItem,
            old_id: str,
            new_id: str
    ):
        """
        Replace temporary attachment with uploaded one

        :param assistant: assistant object
        :param attachment: attachment object
        :param old_id: old id
        :param new_id: new id
        """
        if old_id in assistant.attachments:
            assistant.attachments[new_id] = attachment
            del assistant.attachments[old_id]
            self.save()

    def get_default_assistant(self) -> Optional[str]:
        """
        Return default assistant ID or None

        :return: default assistant
        :rtype: AssistantItem or None
        """
        assistants = self.get_all()
        if len(assistants) == 0:
            return None
        return list(assistants.keys())[0]

    def load(self):
        """Load assistants"""
        self.items = self.provider.load()
        self.store.load()  # load vector stores
        self.files.load()  # load files

    def save(self):
        """Save assistants"""
        self.provider.save(self.items)
