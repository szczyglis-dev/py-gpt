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
import datetime
import os
import re
from pathlib import Path

from .provider.config.json_file import JsonFileProvider


class Config:
    CONFIG_DIR = 'pygpt-net'
    TYPE_STR = 0
    TYPE_INT = 1
    TYPE_FLOAT = 2
    TYPE_BOOL = 3

    def __init__(self, window=None):
        """
        Config handler

        :param window: Window instance
        """
        self.window = window
        self.providers = {}
        self.provider = "json_file"
        self.path = str(Path(os.path.join(Path.home(), '.config', self.CONFIG_DIR)))
        self.initialized = False
        self.initialized_base = False
        self.data = {}
        self.data_base = {}
        self.version = self.get_version()

        # register data providers
        self.add_provider(JsonFileProvider())  # json file provider

    def add_provider(self, provider):
        """
        Add data provider

        :param provider: data provider instance
        """
        self.providers[provider.id] = provider
        self.providers[provider.id].path = self.get_user_path()
        self.providers[provider.id].path_app = self.get_root_path()
        self.providers[provider.id].meta = self.append_meta()
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

    def get_root_path(self):
        """
        Return app data path

        :return: app data path
        :rtype: str
        """
        if __file__.endswith('.pyc'):  # if compiled with pyinstaller
            return os.path.abspath('.')
        else:
            return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    def get_user_path(self):
        """
        Return user home path

        :return: user home path
        :rtype: str
        """
        return self.path

    def init(self, all=True):
        """
        Initialize config

        :param all: load all configs
        """
        if not self.initialized:

            # if app initialization
            if all:
                v = self.get_version()
                os = self.window.app.platform.get_os()
                architecture = self.window.app.platform.get_architecture()
                print("")
                print("PyGPT v{} ({}, {})".format(v, os, architecture))
                print("Author: Marcin Szczyglinski")
                print("GitHub: https://github.com/szczyglis-dev/py-gpt")
                print("WWW: https://pygpt.net")
                print("Email: info@pygpt.net")
                print("")
                print("Initializing...")

                # install all
                self.window.app.installer.install()

            self.load(all)
            self.initialized = True

    def get_version(self):
        """
        Return version

        :return: version string
        :rtype: str
        """
        path = os.path.abspath(os.path.join(self.get_root_path(), '__init__.py'))
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = f.read()
                result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format("__version__"), data)
                return result.group(1)
        except Exception as e:
            if self.window is not None:
                self.window.app.debug.log(e)
            else:
                print("Error loading version file: {}".format(e))

    def get_options(self):
        """
        Return settings options

        :return: settings options
        :rtype: dict
        """
        if self.provider in self.providers:
            try:
                return self.providers[self.provider].get_options()
            except Exception as e:
                if self.window is not None:
                    self.window.app.debug.log(e)
                else:
                    print("Error loading settings options: {}".format(e))
        return {}

    def get(self, key):
        """
        Return config value by key

        :param key: key
        :return: value
        :rtype: Any
        """
        if key in self.data:
            return self.data[key]
        return None

    def set(self, key, value):
        """
        Set config value

        :param key:
        :param value:
        """
        self.data[key] = value

    def has(self, key):
        """
        Check if key exists in config

        :param key: key
        :return: true if exists
        :rtype: bool
        """
        if key in self.data:
            return True
        return False

    def all(self):
        """
        Return all config values

        :return: dict with all config values
        :rtype: dict
        """
        return self.data

    def get_available_langs(self):
        """
        Return list with available languages

        :return: list with available languages (user + app)
        :rtype: list
        """
        langs = []
        path = os.path.join(self.get_root_path(), 'data', 'locale')
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.startswith('locale.') and file.endswith(".ini"):
                    lang_id = file.replace('locale.', '').replace('.ini', '')
                    if lang_id not in langs:
                        langs.append(lang_id)

        path = os.path.join(self.get_user_path(), 'locale')
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.startswith('locale.') and file.endswith(".ini"):
                    lang_id = file.replace('locale.', '').replace('.ini', '')
                    if lang_id not in langs:
                        langs.append(lang_id)

        # make English first
        if 'en' in langs:
            langs.remove('en')
            langs.insert(0, 'en')
        return langs

    def append_meta(self):
        """
        Append meta data

        :return: meta data dict
        :rtype: dict
        """
        return {
            'version': self.version,
            'app.version': self.version,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }

    def load(self, all=True):
        """
        Load config

        :param all: load all configs
        """
        self.load_config(all)

        if all:
            self.window.app.modes.load()
            self.window.app.models.load()
            self.window.app.presets.load()

    def load_config(self, all=True):
        """
        Load user config from JSON file

        :param all: load all configs
        """
        if self.provider in self.providers:
            try:
                self.data = self.providers[self.provider].load(all)
                if self.data is not None:
                    self.data = dict(sorted(self.data.items(), key=lambda item: item[0]))  # sort by key
            except Exception as e:
                if self.window is not None:
                    self.window.app.debug.log(e)
                else:
                    print("Error loading config: {}".format(e))
                self.data = {}

    def load_base_config(self):
        """
        Load app config from JSON file
        """
        if self.provider in self.providers:
            try:
                self.data_base = self.providers[self.provider].load_base()
                if self.data_base is not None:
                    self.data_base = dict(sorted(self.data.items(), key=lambda item: item[0]))  # sort by key
                    self.initialized_base = True
            except Exception as e:
                if self.window is not None:
                    self.window.app.debug.log(e)
                else:
                    print("Error loading config: {}".format(e))
                self.data_base = {}

    def from_base_config(self):
        """
        Load app config from JSON file
        """
        if not self.initialized_base:
            self.load_base_config()
        self.data = copy.deepcopy(self.data_base)

    def get_base(self, option=None):
        """
        Return base config option or all base config

        :param option: option name
        :return: option value or all config
        """
        if not self.initialized_base:
            self.load_base_config()
        if option is None:
            return self.data_base
        elif option in self.data_base:
            return self.data_base[option]

    def save(self, filename='config.json'):
        """
        Save config

        :param filename: filename
        """
        if self.provider in self.providers:
            try:
                self.providers[self.provider].save(self.data, filename)
            except Exception as e:
                if self.window is not None:
                    self.window.app.debug.log(e)
                else:
                    print("Error saving config: {}".format(e))
