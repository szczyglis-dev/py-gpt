#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 10:00:00                  #
# ================================================== #

from packaging.version import parse as parse_version, Version

from ..utils import safe_copy_preset


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: (data, updated, save) - data dict, True if migrated, True if need to save
        """
        migrated = False
        is_llama = False
        is_expert = False
        is_agent_llama = False
        is_agent_assistant = False
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
                    if safe_copy_preset(self.window, 'current.assistant.json'):
                        updated = True

                # < 2.0.102
                if old < parse_version("2.0.102"):
                    if 'current.llama_index' not in self.window.core.presets.items and not is_llama:
                        print("Migrating preset file from < 2.0.102...")
                        if safe_copy_preset(self.window, 'current.llama_index.json'):
                            updated = True
                        is_llama = True  # prevent multiple copies

                # < 2.2.7
                if old < parse_version("2.2.7"):
                    if not is_expert:
                        print("Migrating preset files from < 2.2.7...")
                        copied = False
                        if safe_copy_preset(self.window, 'current.expert.json'):
                            copied = True
                        if safe_copy_preset(self.window, 'current.agent.json'):
                            copied = True
                        if safe_copy_preset(self.window, 'joke_expert.json'):
                            copied = True
                        if copied:
                            updated = True
                        is_expert = True  # prevent multiple copies

                # < 2.4.10
                if old < parse_version("2.4.10"):
                    if 'current.agent_llama' not in self.window.core.presets.items and not is_agent_llama:
                        print("Migrating preset file from < 2.4.10...")
                        files = [
                            'current.agent_llama.json',
                            'agent_simple.json',
                            'agent_planner.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True

                        if copied:
                            updated = True
                        is_agent_llama = True  # prevent multiple copies

                # < 2.4.11
                if old < parse_version("2.4.11"):
                    if 'agent_openai_assistant' not in self.window.core.presets.items and not is_agent_assistant:
                        is_agent_assistant = True  # prevent multiple copies

                # < 2.5.71
                if old < parse_version("2.5.71"):
                    if 'current.computer' not in self.window.core.presets.items and not is_computer:
                        print("Migrating preset file from < 2.5.71...")
                        if safe_copy_preset(self.window, 'current.computer.json'):
                            updated = True
                        is_computer = True  # prevent multiple copies

                # < 2.5.76
                if old < parse_version("2.5.76"):
                    if 'current.agent_openai' not in self.window.core.presets.items and not is_agent_openai:
                        print("Migrating preset file from < 2.5.76...")
                        files = [
                            'current.agent_openai.json',
                            'agent_simple.json',
                            'agent_expert.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True

                        if copied:
                            updated = True
                        is_agent_openai = True  # prevent multiple copies

                # < 2.5.82
                if old < parse_version("2.5.82"):
                    if 'agent_researcher' not in self.window.core.presets.items and not is_bot:
                        print("Migrating preset file from < 2.5.82...")
                        files = [
                            'agent_coder.json',
                            'agent_planner.json',
                            'agent_researcher.json',
                            'agent_writer.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True
                        if copied:
                            updated = True
                        is_bot = True  # prevent multiple copies

                # < 2.5.86
                if old < parse_version("2.5.86"):
                    if 'agent_evolve' not in self.window.core.presets.items and not is_evolve:
                        print("Migrating preset file from < 2.5.86...")
                        files = [
                            'agent_evolve.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True
                        if copied:
                            updated = True
                        is_evolve = True  # prevent multiple copies

                # < 2.5.94
                if old < parse_version("2.5.94"):
                    if 'agent_b2b' not in self.window.core.presets.items and not is_b2b:
                        print("Migrating preset file from < 2.5.94...")
                        files = [
                            'agent_b2b.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True
                        if copied:
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
                    if 'agent_supervisor' not in self.window.core.presets.items and not is_supervisor:
                        print("Migrating preset file from < 2.6.9...")
                        files = [
                            'agent_supervisor.json',
                        ]
                        copied = False
                        for file in files:
                            if safe_copy_preset(self.window, file):
                                copied = True
                        if copied:
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
