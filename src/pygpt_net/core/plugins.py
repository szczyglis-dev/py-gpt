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
import configparser
import io
import os


class Plugins:
    def __init__(self, window):
        """
        Plugins handler

        :param window: Window instance
        """
        self.window = window
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
        plugin.attach(self.window)
        id = plugin.id
        self.plugins[id] = plugin

        # make copy of options
        if hasattr(plugin, 'options'):
            self.plugins[id].initial_options = copy.deepcopy(plugin.options)

        try:
            plugins = self.window.app.config.get('plugins')
            if id in plugins:
                for key in plugins[id]:
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = plugins[id][key]
        except Exception as e:
            self.window.app.errors.log(e)
            print('Error while loading plugin options: {}'.format(id))

    def unregister(self, id):
        """
        Unregister plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins.pop(id)

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

    def dump_locale(self, plugin, path):
        """
        Dump locale

        :param plugin: plugin
        """
        options = {}
        options['plugin.name'] = plugin.name
        options['plugin.description'] = plugin.description

        sorted_keys = sorted(plugin.options.keys())
        for key in sorted_keys:
            option = plugin.options[key]
            if 'label' in option:
                option_key = key + '.label'
                options[option_key] = option['label']
            if 'description' in option:
                option_key = key + '.description'
                options[option_key] = option['description']
            if 'tooltip' in option and option['tooltip'] is not None and option['tooltip'] != '':
                option_key = key + '.tooltip'
                options[option_key] = option['tooltip']

        # dump options to .ini file:
        ini = configparser.ConfigParser()
        ini['LOCALE'] = options

        # save with utf-8 encoding
        with io.open(path, mode="w", encoding="utf-8") as f:
            ini.write(f)

    def dump_locale_by_id(self, id, path):
        """
        Dump locale by id

        :param id: plugin id
        """
        if id in self.plugins:
            self.dump_locale(self.plugins[id], path)

    def dump_plugin_locales(self):
        """
        Dump all locales
        """
        langs = ['en', 'pl']
        for id in self.plugins:
            domain = 'plugin.' + id
            for lang in langs:
                path = os.path.join(self.window.app.config.get_root_path(), 'data', 'locale', domain + '.' + lang + '.ini')
                self.dump_locale(self.plugins[id], path)
