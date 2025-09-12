#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.12 23:00:00                  #
# ================================================== #

import copy
import os

from packaging.version import parse as parse_version, Version

# old patches moved here
from .patches.patch_before_2_6_42 import Patch as PatchBefore2_6_42


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
        cfg_get_base = self.window.core.config.get_base
        patch_css = self.window.core.updater.patch_css
        current = "0.0.0"
        updated = False
        is_old = False

        # get version of config file
        if '__meta__' in data and 'version' in data['__meta__']:
            current = data['__meta__']['version']
        old = parse_version(current)

        # check if config file is older than current app version
        if old < version:

            is_old = True

            # --------------------------------------------
            # previous patches for versions before 2.6.42
            if old < parse_version("2.6.42"):
                patcher = PatchBefore2_6_42(self.window)
                data, updated, _ = patcher.execute(version)
            # --------------------------------------------

            # < 2.6.43
            if old < parse_version("2.6.43"):
                print("Migrating config from < 2.6.43...")
                # li div margin
                patch_css('web-chatgpt.css', True)
                patch_css('web-chatgpt_wide.css', True)
                patch_css('web-blocks.css', True)
                updated = True

            # < 2.6.44
            if old < parse_version("2.6.44"):
                print("Migrating config from < 2.6.44...")
                if "render.code_syntax.stream_n_line" not in data:
                    data["render.code_syntax.stream_n_line"] = 25
                if "render.code_syntax.stream_n_chars" not in data:
                    data["render.code_syntax.stream_n_chars"] = 5000
                if "render.code_syntax.disabled" not in data:
                    data["render.code_syntax.disabled"] = False
                updated = True

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
