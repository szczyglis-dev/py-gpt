#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

import os
import shutil

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
        migrated = False
        is_llama = False
        is_expert = False
        is_agent_llama = False
        is_agent_assistant = False

        for k in self.window.core.presets.items:
            data = self.window.core.presets.items[k]
            updated = False

            # get version of preset
            if data.version is None or data.version == "":
                continue

            old = parse_version(data.version)

            # check if presets file is older than current app version
            if old < version:
                # < 2.0.0
                if old < parse_version("2.0.0"):
                    print("Migrating presets dir from < 2.0.0...")
                    self.window.core.updater.patch_file('presets', True)  # force replace file

                # < 2.0.53
                if old < parse_version("2.0.53") and k == 'current.assistant':
                    print("Migrating preset file from < 2.0.53...")
                    dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.assistant.json')
                    src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets',
                                       'current.assistant.json')
                    shutil.copyfile(src, dst)
                    updated = True
                    print("Patched file: {}.".format(dst))

                # < 2.0.102
                if old < parse_version("2.0.102"):
                    if 'current.llama_index' not in self.window.core.presets.items and not is_llama:
                        print("Migrating preset file from < 2.0.102...")
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.llama_index.json')
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets',
                                           'current.llama_index.json')
                        shutil.copyfile(src, dst)
                        updated = True
                        is_llama = True  # prevent multiple copies
                        print("Patched file: {}.".format(dst))

                # < 2.2.7
                if old < parse_version("2.2.7"):
                    if not is_expert:
                        print("Migrating preset files from < 2.2.7...")
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.expert.json')
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets', 'current.expert.json')
                        shutil.copyfile(src, dst)
                        print("Patched file: {}.".format(dst))
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.agent.json')
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets', 'current.agent.json')
                        shutil.copyfile(src, dst)
                        print("Patched file: {}.".format(dst))
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'joke_expert.json')
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets', 'joke_expert.json')
                        shutil.copyfile(src, dst)
                        print("Patched file: {}.".format(dst))
                        updated = True
                        is_expert = True  # prevent multiple copies

                # < 2.4.10
                if old < parse_version("2.4.10"):
                    if 'current.agent_llama' not in self.window.core.presets.items and not is_agent_llama:
                        print("Migrating preset file from < 2.4.10...")
                        files = [
                            'current.agent_llama.json',
                            'agent_openai.json',
                            'agent_planner.json',
                            'agent_react.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))

                        updated = True
                        is_agent_llama = True  # prevent multiple copies

                # < 2.4.11
                if old < parse_version("2.4.11"):
                    if 'agent_openai_assistant' not in self.window.core.presets.items and not is_agent_assistant:
                        print("Migrating preset file from < 2.4.11...")
                        files = [
                            'agent_openai_assistant.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))

                        updated = True
                        is_agent_assistant = True  # prevent multiple copies

            # update file
            if updated:
                self.window.core.presets.load()  # reload presets from patched files
                self.window.core.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated
