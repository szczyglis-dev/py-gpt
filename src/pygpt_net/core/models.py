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
from packaging.version import Version

from pygpt_net.item.model import ModelItem
from pygpt_net.provider.model.json_file import JsonFileProvider


class Models:

    def __init__(self, window=None):
        """
        Models core

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

    def get(self, model: str) -> ModelItem:
        """
        Return model config

        :param model: model name
        :return: model config object
        :rtype: ModelItem
        """
        if model in self.items:
            return self.items[model]

    def get_by_idx(self, idx: int, mode: str) -> str:
        """
        Return model by index

        :param idx: model idx
        :param mode: mode name
        :return: model name
        """
        items = self.get_by_mode(mode)
        return list(items.keys())[idx]

    def get_by_mode(self, mode: str) -> dict:
        """
        Return models for mode

        :param mode: mode name
        :return: models dict for mode
        """
        items = {}
        for key in self.items:
            if mode in self.items[key].mode:
                items[key] = self.items[key]
        return items

    def has_model(self, mode: str, model: str) -> bool:
        """
        Check if model exists for mode

        :param mode: mode name
        :param model: model name
        :return: True if model exists for mode
        """
        items = self.get_by_mode(mode)
        return model in items

    def get_default(self, mode: str) -> str | None:
        """
        Return default model for mode

        :param mode: mode name
        :return: default model name
        """
        models = {}
        items = self.get_by_mode(mode)
        for k in items:
            models[k] = items[k]
        if len(models) == 0:
            return None
        return list(models.keys())[0]

    def get_tokens(self, model: str) -> int:
        """
        Return model tokens

        :param model: model name
        :return: number of tokens
        """
        if model in self.items:
            return self.items[model].tokens
        return 1

    def get_num_ctx(self, model: str) -> int:
        """
        Return model context window tokens

        :param model: model name
        :return: number of ctx tokens
        """
        if model in self.items:
            return self.items[model].ctx
        return 4096

    def load(self):
        """
        Load models
        """
        self.items = self.provider.load()
        self.items = dict(sorted(self.items.items(), key=lambda item: item[0]))  # sort by key

    def save(self):
        """Save models"""
        self.provider.save(self.items)

    def get_version(self) -> str:
        """Get config version"""
        return self.provider.get_version()
