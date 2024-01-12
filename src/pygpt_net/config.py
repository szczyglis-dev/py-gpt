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

import copy
import datetime
import os
import re
from pathlib import Path

from pygpt_net.provider.config.json_file import JsonFileProvider


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
        
        self.path = str(Path(os.path.join(Path.home(), '.config', self.CONFIG_DIR)))
        self.initialized = False
        self.initialized_base = False
        self.db_echo = False
        self.data = {}
        self.data_base = {}
        self.version = self.get_version()

        self.provider = JsonFileProvider(window)
        self.provider.path = self.get_user_path()
        self.provider.path_app = self.get_app_path()
        self.provider.meta = self.append_meta()

    def is_compiled(self) -> bool:
        """
        Return True if compiled version

        :return: True if compiled
        :rtype: bool
        """
        return  __file__.endswith('.pyc')

    def install(self):
        """Install database and provider data"""
        # install database
        self.window.core.db.echo = self.db_echo
        self.window.core.db.init()

        # install provider configs
        self.provider.install()

    def patch(self, app_version):
        """Patch provider data"""
        self.provider.patch(app_version)

    def get_app_path(self) -> str:
        """
        Return app data path

        :return: app root path
        """
        if self.is_compiled():  # if compiled with pyinstaller
            return os.path.abspath('.')
        else:
            return os.path.abspath(os.path.dirname(__file__))

    def get_user_path(self):
        """
        Return user home path

        :return: user home path
        :rtype: str
        """
        return self.path

    def init(self, all: bool = True):
        """
        Initialize config

        :param all: load all configs
        """
        if not self.initialized:

            # if app initialization
            if all:
                v = self.get_version()
                os = self.window.core.platforms.get_os()
                architecture = self.window.core.platforms.get_architecture()
                print("")
                print("PyGPT v{} ({}, {})".format(v, os, architecture))
                print("Author: Marcin Szczyglinski")
                print("GitHub: https://github.com/szczyglis-dev/py-gpt")
                print("WWW: https://pygpt.net")
                print("Email: info@pygpt.net")
                print("")
                print("Initializing...")

                # install all
                self.window.core.installer.install()

            self.load(all)
            self.initialized = True

    def get_version(self) -> str:
        """
        Return version

        :return: version string
        """
        path = os.path.abspath(os.path.join(self.get_app_path(), '__init__.py'))
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = f.read()
                result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format("__version__"), data)
                return result.group(1)
        except Exception as e:
            if self.window is not None:
                self.window.core.debug.log(e)
            else:
                print("Error loading version file: {}".format(e))

    def get_options(self) -> dict:
        """
        Return settings options

        :return: settings options
        """
        return self.provider.get_options()

    def get(self, key: str) -> any:
        """
        Return config value by key

        :param key: key
        :return: value
        """
        if key in self.data:
            return self.data[key]
        return None

    def set(self, key: str, value: any):
        """
        Set config value

        :param key:
        :param value:
        """
        self.data[key] = value

    def has(self, key: str) -> bool:
        """
        Check if key exists in config

        :param key: key
        :return: True if exists
        """
        if key in self.data:
            return True
        return False

    def all(self) -> dict:
        """
        Return all config values

        :return: dict with all config values
        """
        return self.data

    def get_available_langs(self) -> list:
        """
        Return list with available languages

        :return: list with available languages (user + app)
        """
        langs = []
        path = os.path.join(self.get_app_path(), 'data', 'locale')
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

        # sort by name
        langs.sort()

        # make English first
        if 'en' in langs:
            langs.remove('en')
            langs.insert(0, 'en')

        # make Polish second
        if 'pl' in langs:
            langs.remove('pl')
            langs.insert(1, 'pl')
        return langs

    def append_meta(self) -> dict:
        """
        Append meta data

        :return: meta data dict
        """
        return {
            'version': self.version,
            'app.version': self.version,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }

    def load(self, all: bool = True):
        """
        Load config

        :param all: load all configs
        """
        self.load_config(all)

        if all:
            self.window.core.modes.load()
            self.window.core.models.load()
            self.window.core.presets.load()

    def load_config(self, all: bool = True):
        """
        Load user config from JSON file

        :param all: load all configs
        """
        self.data = self.provider.load(all)
        if self.data is not None:
            self.data = dict(sorted(self.data.items(), key=lambda item: item[0]))  # sort by key

    def load_base_config(self):
        """
        Load app config from JSON file
        """
        self.data_base = self.provider.load_base()
        if self.data_base is not None:
            self.data_base = dict(sorted(self.data.items(), key=lambda item: item[0]))  # sort by key
            self.initialized_base = True

    def from_base_config(self):
        """
        Load app config from JSON file
        """
        if not self.initialized_base:
            self.load_base_config()
        self.data = copy.deepcopy(self.data_base)

    def get_base(self, option: str = None) -> any:
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

    def save(self, filename: str = 'config.json'):
        """
        Save config

        :param filename: filename
        """
        self.provider.save(self.data, filename)
