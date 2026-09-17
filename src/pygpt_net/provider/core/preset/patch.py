#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 09:00:00                  #
# ================================================== #

import os
import shutil

from packaging.version import parse as parse_version, Version

# old patches moved here
from .patches.patch_before_2_6_42 import Patch as PatchBefore2_6_42


AGENT_V2_PRESET_FILES = (
    "agent_v2_pygpt.json",
    "agent_v2_coder.json",
    "agent_v2_researcher.json",
    "agent_v2_scientist.json",
    "agent_v2_brainstorm.json",
    "agent_v2_cybersec.json",
    "agent_v2_osint.json",
    "agent_v2_server_admin.json",
)

class Patch:
    def __init__(self, window=None):
        self.window = window

    def _remove_codeact_2_8_23(self, version: Version) -> bool:
        """Remove the retired CodeAct preset/provider references from user data."""
        target = parse_version("2.8.23")
        if version < target:
            return False

        migrated = False
        preset_path = os.path.join(
            self.window.core.config.get_user_dir("presets"),
            "agent_code_act.json",
        )
        if os.path.exists(preset_path):
            os.remove(preset_path)
            migrated = True
            print("Removed retired preset: {}.".format(preset_path))
            self.window.core.presets.load()

        # Old presets from several modes may still carry the LlamaIndex fallback
        # provider even when that field is not used by their primary mode. Keep
        # every such preset valid after CodeAct is unregistered.
        changed_refs = False
        for preset_id, item in list((self.window.core.presets.items or {}).items()):
            if getattr(item, "agent_provider", None) != "code_act":
                continue
            item.agent_provider = "react"
            self.window.core.presets.save(preset_id)
            changed_refs = True
            migrated = True

        if changed_refs:
            self.window.core.presets.load()

        return migrated

    def _replace_agent_v2_presets_2_8_23(self, version: Version) -> bool:
        """Replace all built-in Agents v2 presets once for the 2.8.23 migration."""
        target = parse_version("2.8.23")
        if version < target:
            return False

        items = self.window.core.presets.items or {}
        needs_replace = False
        for filename in AGENT_V2_PRESET_FILES:
            preset_id = os.path.splitext(filename)[0]
            item = items.get(preset_id)
            stored_version = str(getattr(item, "version", "") or "") if item is not None else ""
            try:
                if item is None or not stored_version or parse_version(stored_version) < target:
                    needs_replace = True
                    break
            except Exception:
                needs_replace = True
                break

        if not needs_replace:
            return False

        print("Migrating Agents v2 presets from < 2.8.23...")
        src_dir = os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "config",
            "presets",
        )
        dst_dir = self.window.core.config.get_user_dir("presets")
        os.makedirs(dst_dir, exist_ok=True)

        for filename in AGENT_V2_PRESET_FILES:
            src = os.path.join(src_dir, filename)
            dst = os.path.join(dst_dir, filename)
            # Intentional destructive migration: 2.8.23 replaces even
            # user-modified copies of these built-in preset files.
            shutil.copyfile(src, dst)
            print("Patched file: {}.".format(dst))

        self.window.core.presets.load()
        return True

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        patcher = PatchBefore2_6_42(self.window)  # old patches (< 2.6.42) moved here
        migrated = patcher.execute(version)

        # 2.8.23 retires CodeAct completely. Remove its user preset and
        # migrate stale fallback references before refreshing Agents v2 presets.
        if self._remove_codeact_2_8_23(version):
            migrated = True

        # 2.8.23 intentionally replaces all built-in Agents v2 preset files,
        # including copies customized by the user before this upgrade.
        if self._replace_agent_v2_presets_2_8_23(version):
            migrated = True

        is_agent_v2 = False
        is_agent_v2_presets = False
        is_agent_v2_cybersec = False
        is_agent_v2_osint = False
        is_agent_v2_server_admin = False

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

            # < 2.8.10
            if old < parse_version("2.8.10"):
                if 'agent_v2_pygpt.json' not in self.window.core.presets.items and not is_agent_v2:
                    files = [
                        'agent_v2_pygpt.json',
                        'current.agent_v2.json',
                    ]
                    for file in files:
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                           'presets', file)
                        shutil.copyfile(src, dst)
                        print("Patched file: {}.".format(dst))
                    updated = True
                    is_agent_v2 = True  # prevent multiple copies

            # < 2.8.11
            if old < parse_version("2.8.11") and not is_agent_v2_presets:
                files = [
                    'agent_v2_brainstorm.json',
                    'agent_v2_coder.json',
                    'agent_v2_researcher.json',
                    'agent_v2_scientist.json',
                ]
                copied = False
                for file in files:
                    dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                    if os.path.exists(dst):
                        continue
                    src = os.path.join(
                        self.window.core.config.get_app_path(),
                        'data',
                        'config',
                        'presets',
                        file,
                    )
                    shutil.copyfile(src, dst)
                    print("Patched file: {}.".format(dst))
                    copied = True
                if copied:
                    updated = True
                is_agent_v2_presets = True  # prevent multiple copy attempts

            # < 2.8.12
            if old < parse_version("2.8.12") and not is_agent_v2_cybersec:
                file = 'agent_v2_cybersec.json'
                dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                if not os.path.exists(dst):
                    print("Migrating Cybersec v2 preset from < 2.8.12...")
                    src = os.path.join(
                        self.window.core.config.get_app_path(),
                        'data',
                        'config',
                        'presets',
                        file,
                    )
                    shutil.copyfile(src, dst)
                    print("Patched file: {}.".format(dst))
                    updated = True
                is_agent_v2_cybersec = True  # prevent multiple copy attempts

            # < 2.8.13
            if old < parse_version("2.8.13") and not is_agent_v2_osint:
                file = 'agent_v2_osint.json'
                dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                if not os.path.exists(dst):
                    print("Migrating OSINT v2 preset from < 2.8.13...")
                    src = os.path.join(
                        self.window.core.config.get_app_path(),
                        'data',
                        'config',
                        'presets',
                        file,
                    )
                    shutil.copyfile(src, dst)
                    print("Patched file: {}.".format(dst))
                    updated = True
                is_agent_v2_osint = True  # prevent multiple copy attempts

            # < 2.8.14
            if old < parse_version("2.8.14") and not is_agent_v2_server_admin:
                file = 'agent_v2_server_admin.json'
                dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                if not os.path.exists(dst):
                    print("Migrating Server Admin v2 preset from < 2.8.14...")
                    src = os.path.join(
                        self.window.core.config.get_app_path(),
                        'data',
                        'config',
                        'presets',
                        file,
                    )
                    shutil.copyfile(src, dst)
                    print("Patched file: {}.".format(dst))
                    updated = True
                is_agent_v2_server_admin = True  # prevent multiple copy attempts

            # update file
            if updated:
                if save:
                    self.window.core.presets.save(k)
                self.window.core.presets.load()  # reload presets from patched files
                self.window.core.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated
