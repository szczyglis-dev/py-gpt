#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 13:00:00
# ================================================== #

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
        data = self.window.core.models.items
        updated = False

        # get version of models config
        current = self.window.core.models.get_version()
        old = parse_version(current)

        # check if models file is older than current app version
        if old < version:

            # --------------------------------------------
            # previous patches for versions before 2.8.32
            if old < parse_version("2.8.32"):
                # old patches moved here
                from .patches.patch_before_2_8_32 import Patch as PatchBefore2_8_32
                patcher = PatchBefore2_8_32(self.window)
                data, updated, _ = patcher.execute(version)
            # --------------------------------------------
            if old < parse_version("2.8.33"):
                from .patches.patch_before_2_8_33 import Patch as PatchBefore2_8_33
                patcher = PatchBefore2_8_33(self.window)
                data, provider_updated, _ = patcher.execute(version)
                updated = updated or provider_updated
            # --------------------------------------------

            # New default models introduced in 2.8.38; preserve user edits.
            if old < parse_version("2.8.38"):
                for model_id in ("gpt-6.1-sol", "claude-opus-5-5", "grok-4.7"):
                    if model_id not in data:
                        model = self.window.core.models.from_base(model_id)
                        if model is not None:
                            data[model_id] = model
                            updated = True

            # DeepSeek V4.1 Flash is added in 2.9.0 without replacing user models.
            if old < parse_version("2.9.0") <= version:
                model_id = "deepseek_api_flash"
                if model_id not in data:
                    model = self.window.core.models.from_base(model_id)
                    if model is not None:
                        data[model_id] = model
                        updated = True

        # update file
        if updated:
            # fix empty/broken data
            for key in list(data.keys()):
                if not data[key]:
                    del data[key]
            data = dict(sorted(data.items()))
            self.window.core.models.items = data
            self.window.core.models.save()

            # also patch any missing models, only if models file is older than 2.5.84
            if old < parse_version("2.5.84"):
                self.window.core.models.patch_missing()

        return updated
