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

from .provider.mode.json_file import JsonFileProvider


class Modes:

    def __init__(self, window=None):
        """
        Config handler

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.initialized = False
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

    def get_by_idx(self, idx):
        """
        Return mode by index

        :param idx: index of mode
        :return: mode name
        :rtype: str
        """
        modes = self.get_all()
        return list(modes.keys())[idx]

    def get_all(self):
        """
        Return modes

        :return: Dict with modes
        :rtype: dict
        """
        return self.items

    def get_default(self):
        """
        Return default mode name

        :return: default mode name
        :rtype: str
        """
        for id in self.items:
            if self.items[id].default:
                return id

    def load(self):
        """
        Load modes
        """
        if self.provider in self.providers:
            try:
                self.items = self.providers[self.provider].load()
            except Exception as e:
                self.window.app.debug.log(e)
                self.items = {}

    def save(self):
        """
        Save modes
        """
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(self.items)
            except Exception as e:
                self.window.app.debug.log(e)
