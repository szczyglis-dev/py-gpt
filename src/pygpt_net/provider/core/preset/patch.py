#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.12 00:00:00                  #
# ================================================== #

import os
import shutil

from packaging.version import parse as parse_version, Version

# old patches moved here
from .patches.patch_before_2_6_42 import Patch as PatchBefore2_6_42

class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        patcher = PatchBefore2_6_42(self.window)  # old patches (< 2.6.42) moved here
        migrated = patcher.execute(version)

        for k in self.window.core.presets.items:
            data = self.window.core.presets.items[k]
            updated = False
            save = False

            # get version of preset
            if data.version is None or data.version == "":
                continue

            # check if presets file is older than current app version
            old = parse_version(data.version)
            if version > old >= parse_version("2.6.42"):
                # --------------------------------------------
                # previous patches for versions before 2.6.42 was moved to external patcher
                # --------------------------------------------

                # > 2.6.42 below:
                pass

            # update file
            if updated:
                if save:
                    self.window.core.presets.save(k)
                self.window.core.presets.load()  # reload presets from patched files
                self.window.core.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated
