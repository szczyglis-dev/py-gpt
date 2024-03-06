#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 22:00:00                  #
# ================================================== #

import json
import os
from packaging.version import Version

from pygpt_net.provider.core.plugin_preset.base import BaseProvider
from .patch import Patch


class JsonFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(JsonFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "json_file"
        self.type = "plugin_presets"
        self.config_file = 'plugin_presets.json'

    def install(self):
        """
        Install provider data files
        """
        dst = os.path.join(self.window.core.config.path, self.config_file)
        if not os.path.exists(dst):
            self.save({})
            print("Installed: {}".format(dst))

    def get_version(self) -> str | None:
        """
        Get config file version

        :return: version
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        if os.path.exists(path):
            with open(path, 'r', encoding="utf-8") as file:
                data = json.load(file)
                if data == "" or data is None:
                    return
                if '__meta__' in data and 'version' in data['__meta__']:
                    return data['__meta__']['version']

    def load(self, all: bool = False) -> dict | None:
        """
        Load config from JSON file

        :return: dict with data or None if file not found
        """
        data = {}
        path = os.path.join(self.window.core.config.path, self.config_file)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                if "items" not in data:
                    return {}
                return data["items"]
        except Exception as e:
            print("FATAL ERROR: {}".format(e))
        return data

    def save(self, items: dict):
        """
        Save presets to JSON file

        :param items: dict with presets
        """
        path = os.path.join(self.window.core.config.path, self.config_file)
        try:
            data = {}
            data['__meta__'] = self.window.core.config.append_meta()
            data['items'] = items
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
        except Exception as e:
            print("FATAL ERROR: {}".format(e))

    def patch(self, version: Version) -> bool:
        """
        Migrate config to current app version

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)
