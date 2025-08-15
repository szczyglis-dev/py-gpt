#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import copy
import datetime
import os
import re

from pathlib import Path
from packaging.version import Version
from operator import itemgetter

from pygpt_net.core.profile import Profile
from pygpt_net.provider.core.config.json_file import JsonFileProvider
from pygpt_net.core.types.console import Color

_RE_VERSION = re.compile(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]')
_RE_BUILD = re.compile(r'__build__\s*=\s*[\'"]([^\'"]*)[\'"]')


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
        self.data = {}
        self.data_base = {}
        self.data_session = {}
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
        self._app_path = None
        self._version_cache = version if version else None
        self._build_cache = None
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
        self.window.core.db.echo = self.db_echo
        self.window.core.db.init()
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
        if not path.exists() and not is_test:
            path.mkdir(parents=True, exist_ok=True)
        path_file = "path.cfg"
        p = os.path.join(str(path), path_file)
        if not os.path.exists(p) and not is_test:
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
        self.initialized_workdir = True
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

        dir_data_allowed = ("img", "capture", "upload")

        if self.has("upload.data_dir") \
                and self.get("upload.data_dir") \
                and dir in dir_data_allowed:
            path = os.path.join(self.get_user_path(), self.dirs["data"], self.dirs[dir])
        else:
            path = os.path.join(self.get_user_path(), self.dirs[dir])
        os.makedirs(path, exist_ok=True)

        return path

    def get_workdir_prefix(self) -> str:
        """
        Return workdir path (sandboxed or user dir)

        :return: workdir path
        """
        workdir = self.get_user_dir('data')
        if self.window.core.plugins.get_option("cmd_code_interpreter", "sandbox_ipython"):
            workdir = "/data"
        return workdir

    def get_app_path(self) -> str:
        """
        Return app data path

        :return: app root path
        """
        if hasattr(self, '_app_path') and self._app_path is not None:
            return self._app_path
        if self.is_compiled():
            self._app_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        else:
            self._app_path = os.path.abspath(os.path.dirname(__file__))
        return self._app_path

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

            if all:
                v = self.get_version()
                build = self.get_build().replace('.', '-')
                os_name = self.window.core.platforms.get_os()
                architecture = self.window.core.platforms.get_architecture()

                print("===================================================")
                print(f" {Color.BOLD}PyGPT    {v}{Color.ENDC} build {build} ({os_name}, {architecture})")
                print(" Author:  Marcin Szczyglinski")
                print(" GitHub:  https://github.com/szczyglis-dev/py-gpt")
                print(" Website: https://pygpt.net")
                print(" Email:   info@pygpt.net")
                print("===================================================")
                print("")
                print(f"{Color.BOLD}Initializing...{Color.ENDC}")

                self.window.core.installer.install()

            self.load(all)
            self.initialized = True

    def get_version(self) -> str:
        """
        Return version

        :return: version string
        """
        if hasattr(self, '_version_cache') and self._version_cache is not None:
            return self._version_cache
        path = os.path.abspath(os.path.join(self.get_app_path(), '__init__.py'))
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = f.read()
                result = _RE_VERSION.search(data)
                self._version_cache = result.group(1)
                return self._version_cache
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
        if self._build_cache is not None:
            return self._build_cache
        path = os.path.abspath(os.path.join(self.get_app_path(), '__init__.py'))
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = f.read()
                result = _RE_BUILD.search(data)
                self._build_cache = result.group(1)
                return self._build_cache
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
        return self.data.get(key, default)

    def get_session(self, key: str, default: any = None) -> any:
        """
        Return session config value by key

        :param key: key
        :param default: default value
        :return: value
        """
        return self.data_session.get(key, default)

    def get_lang(self) -> str:
        """
        Return language code

        :return: language code
        """
        test_lang = os.environ.get('TEST_LANGUAGE')
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
        return key in self.data

    def has_session(self, key: str) -> bool:
        """
        Check if key exists in session config

        :param key: key
        :return: True if exists
        """
        return key in self.data_session

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
        langs_set = set()
        path_app = os.path.join(self.get_app_path(), 'data', 'locale')
        if os.path.exists(path_app):
            for file in os.listdir(path_app):
                if file.startswith('locale.') and file.endswith(".ini"):
                    langs_set.add(file.replace('locale.', '').replace('.ini', ''))
        path_user = os.path.join(self.get_user_path(), 'locale')
        if os.path.exists(path_user):
            for file in os.listdir(path_user):
                if file.startswith('locale.') and file.endswith(".ini"):
                    langs_set.add(file.replace('locale.', '').replace('.ini', ''))
        langs = sorted(langs_set)
        if 'en' in langs:
            langs.remove('en')
            langs.insert(0, 'en')
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
            self.data = dict(sorted(self.data.items(), key=itemgetter(0)))

    def load_base_config(self):
        """
        Load app config from JSON file
        """
        self.data_base = self.provider.load_base()
        if self.data_base is not None:
            self.data_base = dict(sorted(self.data_base.items(), key=itemgetter(0)))
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
        conf = self.all()
        for item in self.data["app.env"]:
            if item['name'] is None or item['name'] == "":
                continue
            try:
                value = str(item['value'].format(**conf))
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