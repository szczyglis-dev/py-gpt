#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.05 16:00:00                  #
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
                    "ctx.annotations.clear_on_send.canvas": False,
                    "ctx.annotations.clear_on_send.files": False,
                    "ctx.annotations.clear_on_send.chat": True,
                }
                for key, value in defaults.items():
                    if key not in data:
                        data[key] = value
                        updated = True

            # --------------------------------------------
            # Application-wide Add-ons storage introduced in 2.8.36.
            if old < parse_version("2.8.36"):
                from .patches.patch_before_2_8_36 import (
                    migrate_addons_to_application_base,
                )
                updated = migrate_addons_to_application_base(self.window) or updated

            if old < parse_version("2.8.38"):
                if "security.computer.show_warning" not in data:
                    data["security.computer.show_warning"] = True
                    updated = True
                if "model.group_providers" not in data:
                    data["model.group_providers"] = False
                    updated = True
                if data.get("access.microphone.notify") is not True:
                    data["access.microphone.notify"] = True
                    updated = True
                if data.get("attachments_capture_clear") is not False:
                    data["attachments_capture_clear"] = False
                    updated = True
                if "agent.v2.show_tools" not in data:
                    data["agent.v2.show_tools"] = False
                    updated = True
                for key in ("filesystem.preview.markdown.font_size", "filesystem.preview.text.font_size"):
                    if key not in data:
                        data[key] = 0  # Use the default font until the first zoom gesture.
                        updated = True

            # Global external-context gateway and project evidence sharing.
            if old < parse_version("2.9.1") <= version:
                from pygpt_net.core.summarizer.summarizer import DEFAULTS
                if "ctx.attachment.project_share" in data:
                    del data["ctx.attachment.project_share"]
                    updated = True
                for key, value in DEFAULTS.items():
                    if key not in data:
                        data[key] = value
                        updated = True

            # Replace all Dockerfile settings on upgrade to 2.9.0, including
            # customized values. Subsequent starts keep the saved settings.
            if old < parse_version("2.9.0") <= version:
                from pygpt_net.plugin.cmd_system.dockerfile import SYSTEM_DOCKERFILE
                from pygpt_net.plugin.cmd_code_interpreter.dockerfile import (
                    IPYTHON_DOCKERFILE,
                    PYTHON_LEGACY_DOCKERFILE,
                )
                plugins = data.setdefault("plugins", {})
                plugins.setdefault("cmd_system", {})["dockerfile"] = SYSTEM_DOCKERFILE
                interpreter = plugins.setdefault("cmd_code_interpreter", {})
                interpreter["dockerfile"] = PYTHON_LEGACY_DOCKERFILE
                interpreter["ipython_dockerfile"] = IPYTHON_DOCKERFILE
                updated = True

        if version >= parse_version("2.9.1"):
            from pygpt_net.plugin.filesystem.migration import migrate_tree, defaults
            if migrate_tree(data, reset_runtime=old < parse_version("2.9.1")):
                updated = True
            # 2.9.1 deliberately replaces customized images and package settings.
            if old < parse_version("2.9.1"):
                config = data.setdefault("plugins", {}).setdefault("filesystem", {})
                for key, option in defaults().items():
                    if option["tab"] == "runtime" and key != "sandbox":
                        config[key] = option["value"]
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
