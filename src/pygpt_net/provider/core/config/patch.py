#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 09:00:00                  #
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
            # provider-scoped API config introduced in 2.8.33
            if old < parse_version("2.8.33"):
                from .patches.patch_before_2_8_33 import Patch as PatchBefore2_8_33
                patcher = PatchBefore2_8_33(self.window)
                data, provider_updated, _ = patcher.execute(version)
                updated = updated or provider_updated
            # --------------------------------------------
            # .agents project-directory support introduced in 2.8.34
            if old < parse_version("2.8.34"):
                for key in (
                    "agent.v2.agents_dir.enabled",
                    "agent.llama.agents_dir.enabled",
                ):
                    if key not in data:
                        data[key] = True
                        updated = True

                # Retired Custom agents/OpenAI-agent settings
                for key in (
                        "agent.openai.response.split",
                ):
                    if key in data:
                        del data[key]
                        updated = True

            # --------------------------------------------
            # Global filesystem text-editor settings and application runtime
            # directories introduced in 2.8.35.
            if old < parse_version("2.8.35"):
                from .patches.patch_before_2_8_35 import (
                    migrate_application_runtime_dirs,
                    migrate_remote_tools,
                )
                migrate_application_runtime_dirs(self.window)
                updated = migrate_remote_tools(data) or updated
                defaults = {
                    "filesystem.text_editor.tabs.indent_spaces": True,
                    "filesystem.text_editor.tabs.width": 4,
                    "filesystem.text_editor.word_wrap": False,
                    "layout.canvas.auto_open": True,
                }
                for key, value in defaults.items():
                    if key not in data:
                        data[key] = value
                        updated = True

                if "layout.canvas.auto_open" not in data:
                    data["layout.canvas.auto_open"] = True
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
