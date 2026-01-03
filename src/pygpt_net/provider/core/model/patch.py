#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 02:10:00                  #
# ================================================== #

from packaging.version import parse as parse_version, Version

from pygpt_net.core.types import (
    MODE_RESEARCH,
    MODE_CHAT,
    MODE_AGENT_OPENAI,
    MODE_COMPUTER,
    MODE_EXPERT
)

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
        data = self.window.core.models.items
        base_data = self.window.core.models.get_base()
        from_base = self.window.core.models.from_base
        updated = False

        # get version of models config
        current = self.window.core.models.get_version()
        old = parse_version(current)

        # check if models file is older than current app version
        if old < version:

            # --------------------------------------------
            # previous patches for versions before 2.6.42
            if old < parse_version("2.6.42"):
                patcher = PatchBefore2_6_42(self.window)
                data, updated = patcher.execute(version)
            # --------------------------------------------

            # <  2.6.66 <--- add models
            if old < parse_version("2.6.66"):
                print("Migrating models from < 2.6.66...")
                models_to_add = [
                    "claude-opus-4-5",
                    "claude-sonnet-4-5",
                    "gemini-3-flash-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-preview",
                    "gpt-5.2-low",
                    "gpt-5.2-medium",
                    "gpt-5.2-high",
                    "gpt-image-1.5",
                    "nano-banana-pro-preview",
                    "sora-2",
                    "veo-3.1-fast-generate-preview",
                    "veo-3.1-generate-preview"
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
                updated = True

            # <  2.6.67 <--- add missing image input
            if old < parse_version("2.6.67"):
                print("Migrating models from < 2.6.67...")
                models_to_update = [
                    "claude-opus-4-5",
                    "claude-sonnet-4-5",
                    "gemini-3-flash-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-3-pro-preview",
                    "gpt-5.2-low",
                    "gpt-5.2-medium",
                    "gpt-5.2-high",
                    "gpt-image-1.5",
                    "nano-banana-pro-preview",
                    "sora-2",
                    "veo-3.1-fast-generate-preview",
                    "veo-3.1-generate-preview"
                ]
                for model in models_to_update:
                    if model in data:
                        m = data[model]
                        if not m.is_image_input():
                            m.input.append("image")
                updated = True

            # <  2.7.5 <--- add: gemini-2.5-computer-use-preview-10-2025
            if old < parse_version("2.7.5"):
                print("Migrating models from < 2.7.5...")
                models_to_add = [
                    "gemini-2.5-computer-use-preview-10-2025",
                    "deep-research-pro-preview-12-2025"
                ]
                for model in models_to_add:
                    if model not in data:
                        base_model = from_base(model)
                        if base_model:
                            data[model] = base_model
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
