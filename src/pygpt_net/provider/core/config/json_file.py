#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.17 21:00:00                  #
# ================================================== #

import json
import os
import shutil
from typing import Optional, Dict, Any

from packaging.version import Version

from pygpt_net.provider.core.config.base import BaseProvider
from .patch import Patch


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "json_file"
        self.type = "config"
        self.config_file = 'config.json'
        self.settings_file = 'settings.json'
        self.sections_file = 'settings_section.json'

    def install(self):
        """Install provider data files"""
        # config file
        dst = os.path.join(self.path, self.config_file)
        if not os.path.exists(dst):
            src = os.path.join(self.path_app, 'data', 'config', self.config_file)
            shutil.copyfile(src, dst)
        else:
            # check if config file is correct - if not, then restore from base config
            try:
                with open(dst, 'r', encoding="utf-8") as file:
                    json.load(file)
            except json.JSONDecodeError:
                print("RECOVERY: Config file `{}` is corrupted. Restoring from base config.".format(dst))
                backup_dst = os.path.join(self.path, 'config.bak.json')
                if os.path.exists(backup_dst):
                    os.remove(backup_dst)
                shutil.copyfile(dst, backup_dst)
                os.remove(dst)
                print("RECOVERY: Backup of corrupted config file created: {}".format(backup_dst))
                src = os.path.join(self.path_app, 'data', 'config', self.config_file)
                shutil.copyfile(src, dst)
                print("RECOVERY: Restored config file from base config: {}".format(src))

        # data tmp
        tmp_dir = os.path.join(self.window.core.config.get_user_dir('data'), 'tmp')
        if not os.path.exists(tmp_dir):
            try:
                os.makedirs(tmp_dir, exist_ok=True)
            except Exception as e:
                print("WARNING: Cannot create ``{}`` data temp directory: {}".format(tmp_dir, e))

        # base tmp
        tmp_dir = os.path.join(self.window.core.config.get_user_path(), 'tmp')
        if not os.path.exists(tmp_dir):
            try:
                os.makedirs(tmp_dir, exist_ok=True)
            except Exception as e:
                print("WARNING: Cannot create ``{}`` base temp directory: {}".format(tmp_dir, e))

    def get_version(self) -> Optional[str]:
        """
        Get config file version

        :return: version
        """
        path = os.path.join(self.path, self.config_file)
        with open(path, 'r', encoding="utf-8") as file:
            data = json.load(file)
            if data == "" or data is None:
                return
            if '__meta__' in data and 'version' in data['__meta__']:
                return data['__meta__']['version']

    def load(self, all: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load config from JSON file

        :param all: if True, print loaded config message
        :return: dict with data or None if file not found
        """
        data = {}
        path = os.path.join(self.path, self.config_file)
        if not os.path.exists(path):
            print("User config: {} not found.".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                if all:
                    print("Loaded config: {}".format(path))
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def load_base(self) -> Optional[Dict[str, Any]]:
        """
        Load config from JSON file

        :return: dict with data or None if file not found
        """
        data = {}
        path = os.path.join(self.path_app, 'data', 'config', self.config_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def save(self, data: Dict[str, Any], filename: str = 'config.json'):
        """
        Save config to JSON file

        :param dict with data: data to save
        :param filename: filename, default: config.json
        """
        path = os.path.join(self.path, filename)
        try:
            data['__meta__'] = self.meta
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))

    def get_options(self) -> Optional[Dict[str, Any]]:
        """
        Load config settings options from JSON file

        :return: dict with data or None if file not found
        """
        data = {}
        path = os.path.join(self.path_app, 'data', 'config', self.settings_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def get_sections(self) -> Optional[Dict[str, Any]]:
        """
        Load config sections from JSON file

        :return: dict with data or None if file not found
        """
        data = {}
        path = os.path.join(self.path_app, 'data', 'config', self.sections_file)
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def patch(self, version: Version) -> bool:
        """
        Migrate config to current app version

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)
