#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 21:00:00                  #
# ================================================== #

import copy
import datetime
import os
import re

from pathlib import Path
from packaging.version import Version

from pygpt_net.core.profile import Profile
from pygpt_net.provider.core.config.json_file import JsonFileProvider


class Config:
    CONFIG_DIR = 'pygpt-net'
    SNAP_NAME = 'pygpt'
    TYPE_STR = 0
    TYPE_INT = 1
    TYPE_FLOAT = 2
    TYPE_BOOL = 3

    def __init__(self, window=None):
        """
        Config handler

        :param window: Window instance
        """
        version = self.get_version()
        self.window = window
        self.profile = Profile(window)
        self.profile.version = version
        self.profile.init(Config.get_base_workdir())
        self.path = None
        self.initialized = False
        self.initialized_base = False
        self.initialized_workdir = False
        self.db_echo = False
        self.data = {}  # user config
        self.data_base = {}  # base config
        self.data_session = {}  # temporary config (session only)
        self.version = version
        self.dirs = {
            "capture": "capture",
            "css": "css",
            "data": "data",
            "history": "history",
            "idx": "idx",
            "ctx_idx": "ctx_idx",
            "img": "img",
            "locale": "locale",
            "presets": "presets",
            "upload": "upload",
            "tmp": "tmp",
        }
        self.provider = JsonFileProvider(window)
        self.provider.path_app = self.get_app_path()
        self.provider.meta = self.append_meta()

        if not self.initialized_workdir:
            workdir = self.prepare_workdir()
            self.set_workdir(workdir)

    def is_compiled(self) -> bool:
        """
        Return True if compiled version

        :return: True if compiled version
        """
        return __file__.endswith('.pyc')

    def install(self):
        """Install database and provider data"""
        self.window.core.db.echo = self.db_echo  # verbose on/off
        self.window.core.db.init()

        # install provider configs
        self.provider.install()

    def get_path(self) -> str:
        """
        Return workdir path

        :return: workdir path
        """
        if not self.initialized_workdir:
            workdir = self.prepare_workdir()
            self.set_workdir(workdir)
        return self.path

    @staticmethod
    def get_base_workdir() -> str:
        """
        Return base workdir path

        :return: base workdir path
        """
        path = os.path.join(Path.home(), '.config', Config.CONFIG_DIR)
        if "PYGPT_WORKDIR" in os.environ and os.environ["PYGPT_WORKDIR"] != "":
            print("FORCE using workdir: {}".format(os.environ["PYGPT_WORKDIR"]))
            # convert relative path to absolute path if needed
            if not os.path.isabs(os.environ["PYGPT_WORKDIR"]):
                path = os.path.join(os.getcwd(), os.environ["PYGPT_WORKDIR"])
            else:
                path = os.environ["PYGPT_WORKDIR"]
            if not os.path.exists(path):
                print("Workdir path not exists: {}".format(path))
                print("Creating workdir path: {}".format(path))
                os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def prepare_workdir() -> str:
        """
        Prepare workdir

        :return: workdir path
        """
        is_test = os.environ.get('ENV_TEST') == '1'
        path = Path(Config.get_base_workdir())
        if not path.exists() and not is_test:  # DISABLE in tests!!!
            path.mkdir(parents=True, exist_ok=True)
        path_file = "path.cfg"
        p = os.path.join(str(path), path_file)
        if not os.path.exists(p) and not is_test:  # DISABLE in tests!!!
            with open(p, 'w', encoding='utf-8') as f:
                f.write("")
        else:
            with open(p, 'r', encoding='utf-8') as f:
                tmp_path = f.read().strip()
            if tmp_path:
                tmp_path = tmp_path.replace("%HOME%", str(Path.home()))
                if os.path.exists(tmp_path):
                    path = Path(tmp_path)
                else:
                    print("CRITICAL: Workdir path not exists: {}".format(tmp_path))
        return str(path)

    def set_workdir(self, path: str, reload: bool = False):
        """
        Update workdir path

        :param path: new path
        :param reload: reload config
        """
        self.path = path
        self.provider.path = path
        if reload:
            self.initialized = False
            self.init(True)

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if patched
        """
        return self.provider.patch(app_version)

    def get_user_dir(self, dir: str) -> str:
        """
        Return user dir

        :param dir: dir name
        :return: user dir
        """
        if dir not in self.dirs:
            raise Exception('Unknown dir: {}'.format(dir))

        dir_data_allowed = ["img", "capture", "upload"]

        if self.has("upload.data_dir") \
                and self.get("upload.data_dir") \
                and dir in dir_data_allowed:
            path = os.path.join(self.get_user_path(), self.dirs["data"], self.dirs[dir])
        else:
            path = os.path.join(self.get_user_path(), self.dirs[dir])
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        return path

    def get_app_path(self) -> str:
        """
        Return app data path

        :return: app root path
        """
        if self.is_compiled():  # if compiled with pyinstaller
            return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        else:
            return os.path.abspath(os.path.dirname(__file__))

    def get_user_path(self) -> str:
        """
        Return user home path (workdir)

        :return: user home path
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
                build = self.get_build()
                os = self.window.core.platforms.get_os()
                architecture = self.window.core.platforms.get_architecture()
                print("===================================================")
                print(" PyGPT    {} build {} ({}, {})".format(v, build.replace('.', '-'), os, architecture))
                print(" Author:  Marcin Szczyglinski")
                print(" GitHub:  https://github.com/szczyglis-dev/py-gpt")
                print(" Website: https://pygpt.net")
                print(" Email:   info@pygpt.net")
                print("===================================================")
                print("")
                print("Initializing...")

                # prepare and install
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

    def get_build(self) -> str:
        """
        Return build

        :return: build string
        """
        path = os.path.abspath(os.path.join(self.get_app_path(), '__init__.py'))
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = f.read()
                result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format("__build__"), data)
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

    def get_sections(self) -> dict:
        """
        Return settings sections

        :return: settings sections
        """
        return self.provider.get_sections()

    def get(self, key: str, default: any = None) -> any:
        """
        Return config value by key

        :param key: key
        :param default: default value
        :return: value
        """
        if key in self.data:
            return self.data[key]
        return default

    def get_session(self, key: str, default: any = None) -> any:
        """
        Return session config value by key

        :param key: key
        :param default: default value
        :return: value
        """
        if key in self.data_session:
            return self.data_session[key]
        return default

    def get_lang(self) -> str:
        """
        Return language code

        :return: language code
        """
        test_lang = os.environ.get('TEST_LANGUAGE')  # if pytest
        if test_lang:
            return test_lang
        return self.get('lang', 'en')

    def set(self, key: str, value: any):
        """
        Set config value

        :param key: key
        :param value: value
        """
        self.data[key] = value

    def set_session(self, key: str, value: any):
        """
        Set session config value

        :param key: key
        :param value: value
        """
        self.data_session[key] = value

    def has(self, key: str) -> bool:
        """
        Check if key exists in config

        :param key: key
        :return: True if exists
        """
        if key in self.data:
            return True
        return False

    def has_session(self, key: str) -> bool:
        """
        Check if key exists in session config

        :param key: key
        :return: True if exists
        """
        if key in self.data_session:
            return True
        return False

    def all(self) -> dict:
        """
        Return all config values

        :return: dict with all config values
        """
        return self.data

    def all_session(self) -> dict:
        """
        Return all session config values

        :return: dict with all config values
        """
        return self.data_session

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
            self.window.core.plugins.load_presets()

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
            self.data_base = dict(sorted(self.data_base.items(), key=lambda item: item[0]))  # sort by key
            self.initialized_base = True

    def from_base_config(self):
        """
        Load app config from JSON file
        """
        if not self.initialized_base:
            self.load_base_config()
        self.data = copy.deepcopy(self.data_base)

    def get_last_used_dir(self) -> str:
        """
        Return last used directory

        :return: last used directory
        """
        last_dir = self.get_user_dir("data")
        if self.has("dialog.last_dir"):
            tmp_dir = self.get("dialog.last_dir")
            if os.path.isdir(tmp_dir):
                last_dir = tmp_dir
        return last_dir

    def set_last_used_dir(self, path: str):
        """
        Save last used directory

        :param path: path
        """
        self.set('dialog.last_dir', path)
        self.save()

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

    def replace_key(self, data: dict, key_from: str, key_to: str) -> dict:
        """
        Replace key in dict

        :param data: dict
        :param key_from: key to replace
        :param key_to: new key
        :return: dict with replaced keys
        """
        if key_from in data:
            data[key_to] = copy.deepcopy(data[key_from])
            del data[key_from]
        return data

    def setup_env(self):
        """Setup environment vars"""
        if "app.env" not in self.data or not isinstance(self.data["app.env"], list):
            return
        list_loaded = []
        for item in self.data["app.env"]:
            if item['name'] is None or item['name'] == "":
                continue
            try:
                value = str(item['value'].format(**self.all()))
                os.environ[item['name']] = value
                list_loaded.append(item['name'])
            except Exception as e:
                print("Error setting env var: {}".format(e))
        if list_loaded:
            print("Setting environment vars: {}".format(", ".join(list_loaded)))

    def save(self, filename: str = "config.json"):
        """
        Save config

        :param filename: filename
        """
        self.provider.save(self.data, filename)
