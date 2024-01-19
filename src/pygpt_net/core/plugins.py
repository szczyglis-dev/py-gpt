#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 18:00:00                  #
# ================================================== #

import copy
import configparser
import io
import os

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window):
        """
        Plugins core

        :param window: Window instance
        """
        self.window = window
        self.allowed_types = [
            'audio.input',
            'audio.output',
            'text.input',
            'text.output',
            'vision',
            'schedule'
        ]
        self.plugins = {}

    def is_registered(self, id: str) -> bool:
        """
        Check if plugin is registered

        :param id: plugin id
        :return: True if registered
        """
        return id in self.plugins

    def all(self) -> dict:
        """
        Get all plugins

        :return: plugins dict
        """
        return self.plugins

    def get_ids(self) -> list:
        """
        Get all plugins ids

        :return: plugins ids list
        """
        return list(self.plugins.keys())

    def get(self, id: str) -> BasePlugin or None:
        """
        Get plugin by id

        :param id: plugin id
        :return: plugin instance
        """
        if self.is_registered(id):
            return self.plugins[id]
        return None

    def register(self, plugin: any):
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

            # register options (configure dict editors, etc.)
            self.register_options(id, self.plugins[id].options)
            # print("Loaded plugin: {}".format(plugin.name))
        except Exception as e:
            self.window.core.debug.log(e)
            print('Error while loading plugin options: {}'.format(id))

    def register_options(self, id: str, options: dict):
        """
        Register plugin options

        :param id: plugin id
        :param options: options dict
        """
        for key in options:
            option = options[key]
            if 'type' in option and option['type'] == 'dict':
                parent = "plugin." + id
                option['label'] = key
                self.window.ui.dialogs.register_dictionary(key, parent, option)

    def unregister(self, id: str):
        """
        Unregister plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins.pop(id)

    def enable(self, id: str):
        """
        Enable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = True
            self.window.core.config.data['plugins_enabled'][id] = True
            self.window.core.config.save()

    def disable(self, id: str):
        """
        Disable plugin

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].enabled = False
            self.window.core.config.data['plugins_enabled'][id] = False
            self.window.core.config.save()

    def destroy(self, id: str):
        """
        Destroy plugin workers (send stop signal)

        :param id: plugin id
        """
        if self.is_registered(id):
            self.plugins[id].destroy()

    def has_options(self, id: str) -> bool:
        """
        Check if plugin has options

        :param id: plugin id
        :return: True if has options
        """
        if self.is_registered(id):
            return hasattr(self.plugins[id], 'options') and len(self.plugins[id].options) > 0
        return False

    def restore_options(self, id: str):
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

    def get_name(self, id: str) -> str:
        """
        Get plugin name (translated)

        :param id: plugin id
        :return: plugin name
        """
        plugin = self.get(id)
        default = plugin.name
        trans_key = 'plugin.' + id
        name = trans(trans_key)
        if name == trans_key:
            name = default
        if plugin.use_locale:
            domain = 'plugin.{}'.format(id)
            name = trans('plugin.name', domain=domain)
        return name

    def get_desc(self, id: str) -> str:
        """
        Get description (translated)

        :param id: plugin id
        :return: plugin description
        """
        plugin = self.get(id)
        default = plugin.description
        trans_key = 'plugin.' + id + '.description'
        tooltip = trans(trans_key)
        if tooltip == trans_key:
            tooltip = default
        if plugin.use_locale:
            domain = 'plugin.{}'.format(id)
            tooltip = trans('plugin.description', domain=domain)
        return tooltip

    def dump_locale(self, plugin, path: str):
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

    def dump_locale_by_id(self, id: str, path: str):
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
