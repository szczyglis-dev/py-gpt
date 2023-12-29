#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

import copy
import configparser
import io
import os


class Plugins:
    def __init__(self, window):
        """
        Plugins core

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

    def all(self):
        """
        Get all plugins

        :return: plugins dict
        :rtype: dict
        """
        return self.plugins

    def get_ids(self):
        """
        Get all plugins ids

        :return: plugins ids
        :rtype: list
        """
        return self.plugins.keys()

    def get(self, id):
        """
        Get plugin by id

        :param id: plugin id
        :return: plugin instance
        """
        if self.is_registered(id):
            return self.plugins[id]
        return None

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
            plugins = self.window.core.config.get('plugins')
            if id in plugins:
                for key in plugins[id]:
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = plugins[id][key]
        except Exception as e:
            self.window.core.debug.log(e)
            print('Error while loading plugin options: {}'.format(id))

    def unregister(self, id):
        """
        Unregister plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins.pop(id)

    def enable(self, id):
        """
        Enable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = True
            self.window.core.config.data['plugins_enabled'][id] = True
            self.window.core.config.save()

    def disable(self, id):
        """
        Disable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = False
            self.window.core.config.data['plugins_enabled'][id] = False
            self.window.core.config.save()

    def destroy(self, id):
        """
        Destroy plugin workers (send stop signal)

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].destroy()

    def has_options(self, id):
        """
        Check if plugin has options

        :param id: plugin id
        :return: true if has options
        :rtype: bool
        """
        if self.is_registered(id):
            return hasattr(self.plugins[id], 'options') and len(self.plugins[id].options) > 0
        return False

    def restore_options(self, id):
        """
        Restore options to initial values

        :param id: plugin id
        """
        options = []
        values = {}
        for key in self.plugins[id].options:
            if 'persist' in self.plugins[id].options[key] and self.plugins[id].options[key]['persist']:
                options.append(key)

        # store persisted values
        for key in options:
            values[key] = self.plugins[id].options[key]['value']

        # restore initial values
        if id in self.plugins:
            if hasattr(self.plugins[id], 'initial_options'):
                self.plugins[id].options = copy.deepcopy(self.plugins[id].initial_options)  # copy

        # restore persisted values
        for key in options:
            self.plugins[id].options[key]['value'] = values[key]

    def dump_locale(self, plugin, path):
        """
        Dump locale

        :param plugin: plugin
        :param path: path to locale file
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
        :param path: path to locale file
        """
        if id in self.plugins:
            self.dump_locale(self.plugins[id], path)

    def dump_locales(self):
        """
        Dump all locales
        """
        langs = ['en', 'pl']
        for id in self.plugins:
            domain = 'plugin.' + id
            for lang in langs:
                path = os.path.join(
                    self.window.core.config.get_app_path(), 'data', 'locale', domain + '.' + lang + '.ini')
                self.dump_locale(self.plugins[id], path)
