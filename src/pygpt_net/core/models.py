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

from pygpt_net.core.provider.model.json_file import JsonFileProvider


class Models:

    def __init__(self, window=None):
        """
        Config handler

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

    def install(self):
        """Install provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].install()
            except Exception as e:
                self.window.app.debug.log(e)

    def patch(self, app_version):
        """Patch provider data"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].patch(app_version)
            except Exception as e:
                self.window.app.debug.log(e)

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
        if self.provider in self.providers:
            try:
                self.items = self.providers[self.provider].load()
                self.items = dict(sorted(self.items.items(), key=lambda item: item[0]))  # sort by key
            except Exception as e:
                self.window.app.debug.log(e)
                self.items = {}

    def save(self):
        """Save models"""
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(self.items)
            except Exception as e:
                self.window.app.debug.log(e)

    def get_version(self):
        """Get config version"""
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].get_version()
            except Exception as e:
                self.window.app.debug.log(e)
