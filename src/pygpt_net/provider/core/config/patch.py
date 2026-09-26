#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 13:00:00                  #
# ================================================== #

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
        data = self.window.core.config.all()
        current = "0.0.0"
        updated = False
        is_old = False

        # get version of config file
        if '__meta__' in data and 'version' in data['__meta__']:
            current = data['__meta__']['version']
        old = parse_version(current)

        # Remove obsolete global sampling controls even when the stored config
        # already has the current version. They are no longer exposed or sent
        # by PyGPT and should not linger in user config files.
        for key in (
            "presence_penalty",
            "frequency_penalty",
            "temperature",
            "top_p",
        ):
            if key in data:
                del data[key]
                updated = True

        # check if config file is older than current app version
        if old < version:

            is_old = True

            # --------------------------------------------
            # previous patches for versions before 2.8.32
            if old < parse_version("2.8.32"):
                # old patches moved here
                from .patches.patch_before_2_8_32 import Patch as PatchBefore2_8_32
                patcher = PatchBefore2_8_32(self.window)
                data, updated, _ = patcher.execute(version)
            # --------------------------------------------

        # update file
        migrated = False
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.config.data = data
            self.window.core.config.save()
            migrated = True

        # check for any missing config keys if versions mismatch
        if is_old:
            if self.window.core.updater.post_check_config():
                migrated = True

        return migrated
