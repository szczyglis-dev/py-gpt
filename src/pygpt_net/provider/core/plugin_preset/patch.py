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

import os

from packaging.version import parse as parse_version, Version


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate config to current app version

        :param version: current app version
        :return: True if migrated
        """
        data = self.window.core.plugins.get_presets()
        current = "0.0.0"
        updated = False
        is_old = False

        # get version of config file
        if '__meta__' in data and 'version' in data['__meta__']:
            current = data['__meta__']['version']
        old = parse_version(current)

        # check if config file is older than current app version
        if old < version:

            # mark as older version
            is_old = True

            # < 0.9.1
            if old < parse_version("2.1.10"):
                print("Migrating presets from < 2.1.10...")
                pass
                updated = True

        # update file
        migrated = False
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.plugins.presets = data
            self.window.core.plugins.save_presets()
            migrated = True

        return migrated
