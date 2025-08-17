#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
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
        is_agent_code_act = False
        is_agent_react_workflow = False
        is_agent_openai = False
        is_computer = False
        is_bot = False
        is_evolve = False
        is_b2b = False
        is_workflow = False
        is_supervisor = False

        for k in self.window.core.presets.items:
            data = self.window.core.presets.items[k]
            updated = False
            save = False

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

                # < 2.5.33
                if old < parse_version("2.5.33"):
                    if 'agent_code_act' not in self.window.core.presets.items and not is_agent_code_act:
                        print("Migrating preset file from < 2.5.33...")
                        files = [
                            'agent_code_act.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))

                        updated = True
                        is_agent_code_act = True  # prevent multiple copies

                # < 2.5.71
                if old < parse_version("2.5.71"):
                    if 'current.computer' not in self.window.core.presets.items and not is_computer:
                        print("Migrating preset file from < 2.5.71...")
                        dst = os.path.join(self.window.core.config.get_user_dir('presets'), 'current.computer.json')
                        src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config', 'presets',
                                           'current.computer.json')
                        shutil.copyfile(src, dst)
                        updated = True
                        is_computer = True  # prevent multiple copies
                        print("Patched file: {}.".format(dst))

                # < 2.5.76
                if old < parse_version("2.5.76"):
                    if 'current.agent_openai' not in self.window.core.presets.items and not is_agent_openai:
                        print("Migrating preset file from < 2.5.76...")
                        files = [
                            'current.agent_openai.json',
                            'agent_openai_simple.json',
                            'agent_openai_expert.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))

                        updated = True
                        is_agent_openai = True  # prevent multiple copies

                # < 2.5.82
                if old < parse_version("2.5.82"):
                    if 'agent_openai_researcher' not in self.window.core.presets.items and not is_bot:
                        print("Migrating preset file from < 2.5.82...")
                        files = [
                            'agent_openai_coder.json',
                            'agent_openai_planner.json',
                            'agent_openai_researcher.json',
                            'agent_openai_writer.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))
                        updated = True
                        is_bot = True  # prevent multiple copies

                # < 2.5.86
                if old < parse_version("2.5.86"):
                    if 'agent_openai_evolve' not in self.window.core.presets.items and not is_evolve:
                        print("Migrating preset file from < 2.5.86...")
                        files = [
                            'agent_openai_evolve.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))
                        updated = True
                        is_evolve = True  # prevent multiple copies

                # < 2.5.94
                if old < parse_version("2.5.94"):
                    if 'agent_openai_b2b' not in self.window.core.presets.items and not is_b2b:
                        print("Migrating preset file from < 2.5.94...")
                        files = [
                            'agent_openai_b2b.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))
                        updated = True
                        is_b2b = True  # prevent multiple copies

                # < 2.6.1
                if old < parse_version("2.6.1"):
                    if data.agent_provider == "react_workflow":
                        data.agent_provider = "react"
                        updated = True
                        save = True

                # < 2.6.9
                if old < parse_version("2.6.9"):
                    if 'agent_openai_supervisor' not in self.window.core.presets.items and not is_supervisor:
                        print("Migrating preset file from < 2.6.9...")
                        files = [
                            'agent_openai_supervisor.json',
                            'agent_supervisor.json',
                        ]
                        for file in files:
                            dst = os.path.join(self.window.core.config.get_user_dir('presets'), file)
                            src = os.path.join(self.window.core.config.get_app_path(), 'data', 'config',
                                               'presets', file)
                            shutil.copyfile(src, dst)
                            print("Patched file: {}.".format(dst))
                        updated = True
                        is_supervisor = True  # prevent multiple copies

            # update file
            if updated:
                if save:
                    self.window.core.presets.save(k)
                self.window.core.presets.load()  # reload presets from patched files
                self.window.core.presets.save(k)  # re-save presets
                migrated = True
                print("Preset {} patched to version {}.".format(k, version))

        return migrated
