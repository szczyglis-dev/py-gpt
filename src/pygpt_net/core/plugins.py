#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 22:00:00                  #
# ================================================== #

import copy

from .dispatcher import Event


class Plugins:
    def __init__(self, config):
        """
        Plugins handler

        :param config: Config instance
        """
        self.config = config
        self.allowed_types = ['audio.input', 'audio.output', 'text.input', 'text.output']
        self.plugins = {}

    def is_registered(self, id):
        """
        Check if plugin is registered

        :param id: plugin id
        :return: true if registered
        :rtype: bool
        """
        return id in self.plugins

    def register(self, plugin):
        """
        Register plugin

        :param plugin: plugin instance
        """
        id = plugin.id
        self.plugins[id] = plugin

        # make copy of options
        if hasattr(plugin, 'options'):
            self.plugins[id].initial_options = copy.deepcopy(plugin.options)

        try:
            plugins = self.config.get('plugins')
            if id in plugins:
                for key in plugins[id]:
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = plugins[id][key]
        except Exception as e:
            print('Error while loading plugin options: {}'.format(id))
            print(e)

    def restore_options(self, id):
        """
        Restore options to initial values

        :param id: plugin id
        """
        persisted_options = []
        persisted_values = {}
        for key in self.plugins[id].options:
            if 'persist' in self.plugins[id].options[key] and self.plugins[id].options[key]['persist']:
                persisted_options.append(key)

        # store persisted values
        for key in persisted_options:
            persisted_values[key] = self.plugins[id].options[key]['value']

        # restore initial values
        if id in self.plugins:
            if hasattr(self.plugins[id], 'initial_options'):
                self.plugins[id].options = dict(self.plugins[id].initial_options)

        # restore persisted values
        for key in persisted_options:
            self.plugins[id].options[key]['value'] = persisted_values[key]
