#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from pygpt_net.provider.model.json_file import JsonFileProvider


class Models:

    def __init__(self, window=None):
        """
        Config handler

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def get(self, model):
        """
        Return model config

        :param model: model name
        :return: model config object
        :rtype: ModelItem
        """
        if model in self.items:
            return self.items[model]

    def get_by_idx(self, idx, mode):
        """
        Return model by index

        :param idx: model idx
        :param mode: mode name
        :return: model name
        :rtype: str
        """
        items = self.get_by_mode(mode)
        return list(items.keys())[idx]

    def get_by_mode(self, mode):
        """
        Return models for mode

        :param mode: mode name
        :return: models dict for mode
        :rtype: dict
        """
        items = {}
        for key in self.items:
            if mode in self.items[key].mode:
                items[key] = self.items[key]
        return items

    def get_default(self, mode):
        """
        Return default model for mode

        :param mode: mode name
        :return: default model name
        :rtype: str
        """
        models = {}
        items = self.get_by_mode(mode)
        for k in items:
            models[k] = items[k]
        if len(models) == 0:
            return None
        return list(models.keys())[0]

    def get_tokens(self, model):
        """
        Return model tokens

        :param model: model name
        :return: number of tokens
        :rtype: int
        """
        if model in self.items:
            return self.items[model].tokens
        return 1

    def get_num_ctx(self, model):
        """
        Return model context window tokens

        :param model: model name
        :return: number of ctx tokens
        :rtype: int
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

    def get_version(self):
        """Get config version"""
        return self.provider.get_version()
