#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:55:00                  #
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
