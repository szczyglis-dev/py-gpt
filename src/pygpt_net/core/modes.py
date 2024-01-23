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

from pygpt_net.provider.core.mode.json_file import JsonFileProvider


class Modes:

    def __init__(self, window=None):
        """
        Modes core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.initialized = False
        self.items = {}

    def get_by_idx(self, idx):
        """
        Return mode by index

        :param idx: index of mode
        :return: mode name
        :rtype: str
        """
        modes = self.get_all()
        return list(modes.keys())[idx]

    def get_idx_by_name(self, name):
        """
        Return mode index by name

        :param name: mode name
        :return: mode index
        :rtype: int
        """
        modes = self.get_all()
        return list(modes.keys()).index(name)

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
        self.items = self.provider.load()

    def save(self):
        """
        Save modes
        """
        self.provider.save(self.items)
