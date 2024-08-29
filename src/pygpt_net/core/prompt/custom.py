#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.29 05:00:00                  #
# ================================================== #

import copy

from PySide6.QtGui import QAction, QIcon
from packaging.version import Version

from pygpt_net.item.prompt import PromptItem
from pygpt_net.provider.core.prompt.json_file import JsonFileProvider
from pygpt_net.utils import trans


class Custom:
    def __init__(self, window=None):
        """
        Custom prompts core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.items = {}
        self.current = None
        self.initiated = False

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def select(self, id: str):
        """
        Select prompt by uuid

        :param id: id
        """
        if id in self.items:
            self.current = id

    def count(self) -> int:
        """
        Count prompts

        :return: prompts count
        """
        return len(self.items)

    def get_ids(self) -> list:
        """
        Get items IDs

        :return: items UUIDs
        """
        return list(self.items.keys())

    def get_id_by_idx(self, idx: int) -> str or None:
        """
        Get ID by index

        :param idx: index
        :return: file ID
        """
        i = 0
        for id in self.get_ids():
            if i == idx:
                return id
            i += 1

    def get_by_id(self, id: str) -> PromptItem or None:
        """
        Return prompt by ID

        :param id: file id
        :return: PromptItem
        """
        if id in self.items:
            return self.items[id]

    def get_by_idx(self, idx: int) -> PromptItem or None:
        """
        Return item by index

        :param idx: item index
        :return: PromptItem or None
        """
        id = self.get_id_by_idx(idx)
        if id is not None:
            return self.items[id]

    def get_all(self) -> dict:
        """
        Return all items

        :return: prompts items dict
        """
        return self.items

    def new(
            self,
            name: str = None,
            content: str = None,
            auto_save: bool = True
    ) -> PromptItem:
        """
        Create new prompt

        :param name: name
        :param content: content
        :param auto_save: auto_save
        :return: PromptItem
        """
        prompt = self.create()
        prompt.name = name
        prompt.content = content

        self.items[prompt.id] = prompt
        self.current = prompt.id

        if auto_save:
            self.save()

        return prompt

    def build(self) -> PromptItem:
        """
        Build prompt

        :return: PromptItem
        """
        prompt = PromptItem()
        prompt.name = None
        prompt.content = None
        return prompt

    def create(self) -> PromptItem:
        """
        Create prompt item

        :return: PromptItem
        """
        prompt = self.build()
        id = self.provider.create(prompt)
        prompt.id = id
        return prompt

    def add(self, item: PromptItem):
        """
        Add item to prompts

        :param item: item to add to prompts
        """
        id = item.id
        self.items[id] = item  # add item to prompts

        # save prompts
        self.save()

    def has(self) -> bool:
        """
        Check id mode has prompts

        :return: True if exists
        """
        return len(self.items) > 0

    def delete(self, id: str):
        """
        Delete prompt by file_id

        :param id: file id
        """
        if id in self.items:
            del self.items[id]
            self.save()

    def delete_all(self):
        """
        Delete all prompts
        """
        self.clear()
        self.provider.truncate()

    def clear(self):
        """
        Clear all prompts

        :param mode: mode
        :param remove_local: remove local copy
        """
        self.items = {}

    def clear_all(self):
        """
        Clear all prompts
        """
        self.items = {}

    def rename_file(self, id: str, name: str):
        """
        Update name

        :param id: file id
        :param name: new name
        """
        data = self.get_by_id(id)
        data.name = name
        self.save()

    def make_json_list(self, prompts: dict) -> dict:
        """
        Make json list

        :param prompts: prompts
        :return: json list
        """
        result = {}
        for id in prompts:
            prompt = prompts[id]
            result[id] = {
                'name': prompt.name,
                'content': prompt.content,
            }
        return result

    def reload(self):
        """Reload prompts"""
        self.items = self.provider.load()

    def load(self):
        """Load prompts"""
        self.items = self.provider.load()

    def save(self):
        """Save prompts"""
        data = copy.deepcopy(self.items)  # copy to avoid changing original data
        self.provider.save(data)

    def init(self):
        """Init prompts"""
        if not self.initiated:
            self.load()
            self.initiated = True

    def to_menu_options(self, menu, parent: str = "global"):
        """
        Convert prompts to menu options

        :param menu: menu
        :param parent: parent
        """
        self.init()

        # at first clear menu
        menu.addSeparator()
        submenu = menu.addMenu(trans("preset.prompt.paste_custom"))
        submenu.clear()
        letter_submenus = {}

        # add submenus for each letter
        for id in self.items.keys():
            value = self.items[id]
            if value.name is None or value.name == "":
                continue
            letter = value.name[0].upper()
            if letter not in letter_submenus:
                letter_submenus[letter] = submenu.addMenu(letter)

        # add prompts to letter submenus
        for id in self.items.keys():
            value = self.items[id]
            if value.name is None or value.name == "":
                continue
            letter = value.name[0].upper()
            item_submenu = letter_submenus[letter].addMenu(value.name)

            action_use = QAction(QIcon(":/icons/paste.svg"), trans("preset.prompt.use"), menu)
            action_use.triggered.connect(lambda checked=False, key=id: self.window.controller.presets.paste_custom_prompt(key, parent))
            action_use.setToolTip(value.content)

            action_rename = QAction(QIcon(":/icons/edit.svg"), trans("preset.prompt.rename"), menu)
            action_rename.triggered.connect(lambda checked=False, key=id: self.window.controller.presets.rename_prompt(key))

            action_delete = QAction(QIcon(":/icons/delete.svg"), trans("preset.prompt.delete"), menu)
            action_delete.triggered.connect(
                lambda checked=False, key=id: self.window.controller.presets.delete_prompt(key))

            item_submenu.addAction(action_use)
            item_submenu.addAction(action_rename)
            item_submenu.addAction(action_delete)
