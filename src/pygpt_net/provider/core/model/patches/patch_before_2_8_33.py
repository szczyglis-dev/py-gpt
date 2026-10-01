#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from packaging.version import parse as parse_version, Version

from pygpt_net.provider.core.config.patches.patch_before_2_8_33 import rewrite_placeholders


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version):
        """Rewrite LlamaIndex model placeholders to provider-scoped config."""
        data = self.window.core.models.items
        current = self.window.core.models.get_version()
        old = parse_version(current)
        if old >= parse_version("2.8.33") or old >= version:
            return data, False, False

        print("Migrating LlamaIndex provider placeholders from < 2.8.33...")
        updated = False
        for model in data.values():
            options = getattr(model, "llama_index", None)
            if not isinstance(options, dict):
                continue
            rewritten = rewrite_placeholders(options)
            if rewritten != options:
                model.llama_index = rewritten
        updated = True
        return data, updated, True
