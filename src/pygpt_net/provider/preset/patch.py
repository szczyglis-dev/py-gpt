#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 10:00:00                  #
# ================================================== #

import os
import shutil

from packaging.version import parse as parse_version, Version


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        migrated = False
        for k in self.window.core.presets.items:
            data = self.window.core.presets.items[k]
            updated = False

            # get version of preset
            old = parse_version(data.version)

            # check if presets file is older than current app version
            if old < version:
                # < 2.0.0
                if old < parse_version("2.0.0"):
                    print("Migrating presets dir from < 2.0.0...")
                    self.window.core.updater.patch_file('presets', True)  # force replace file

                # < 2.0.53
                if old < parse_version("2.0.53") and k == 'current.assistant':
                    print("Migrating preset file from < 2.0.53...")
                    dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.assistant.json')
                    src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets',
                                       'current.assistant.json')
                    shutil.copyfile(src, dst)
                    updated = True
                    print("Patched file: {}.".format(dst))

            # update file
            if updated:
                self.window.core.presets.load()  # reload presets from patched files
                self.window.core.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated
