#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 04:00:00                  #
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

            # < 0.9.1
            if old < parse_version("0.9.1"):
                # apply meta only (not attached in 0.9.0)
                print("Migrating models from < 0.9.1...")
                updated = True

            # < 2.0.1
            if old < parse_version("2.0.1"):
                print("Migrating models from < 2.0.1...")
                self.window.core.updater.patch_file('models.json', True)  # force replace file
                self.window.core.models.load()
                data = self.window.core.models.items
                updated = True

            # < 2.0.96  <--- patch for llama-index modes
            if old < parse_version("2.0.96"):
                print("Migrating models from < 2.0.96...")
                self.window.core.updater.patch_file('models.json', True)  # force replace file
                self.window.core.models.load()
                data = self.window.core.models.items
                updated = True

            # < 2.0.104  <--- patch for llama-index gpt4-turbo
            if old < parse_version("2.0.104"):
                print("Migrating models from < 2.0.104...")
                self.window.core.updater.patch_file('models.json', True)  # force replace file
                self.window.core.models.load()
                data = self.window.core.models.items
                updated = True

            '''
            # < 2.0.104  <--- patch to new format
            if old < parse_version("2.0.104"):
                print("Migrating models from < 2.0.104...")
                for id in data:
                    model = data[id]
                    dict_name = model.to_dict()
                    model.from_dict(dict_name)

                    # patch missing llama_index provider
                    if "llama_index" in model.mode:
                        if model.id.startswith("gpt-") or model.id.startswith("text-davinci-"):
                            model.llama_index["provider"] = "openai"
                            if model.id.startswith("gpt-"):
                                model.llama_index['mode'] = ["chat"]
                            model.llama_index['args'] = [
                                {
                                    "name": "model_name",
                                    "value": model.id,
                                    "type": "str",
                                }
                            ]
                            model.llama_index['env'] = [
                                {
                                    "name": "OPENAI_API_KEY",
                                    "value": "{api_key}",
                                }
                            ]
                    if "langchain" in model.mode:
                        if model.id.startswith("gpt-") or model.id.startswith("text-davinci-"):
                            model.langchain['args'] = [
                                {
                                    "name": "model_name",
                                    "value": model.id,
                                    "type": "str",
                                }
                            ]
                            model.langchain['env'] = [
                                {
                                    "name": "OPENAI_API_KEY",
                                    "value": "{api_key}",
                                }
                            ]
                updated = True
            '''

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.models.items = data
            self.window.core.models.save()

        return updated
