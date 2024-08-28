#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 01:00:00                  #
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
        is_old = False
        if old < version:
            is_old = True

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

            # < 2.0.105  <--- patch for llama-index gpt4-turbo
            if old < parse_version("2.0.105"):
                print("Migrating models from < 2.0.105...")
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

            # < 2.0.107  <--- patch for deprecated davinci, replace with gpt-3.5-turbo-instruct
            if old < parse_version("2.0.107"):
                print("Migrating models from < 2.0.107...")
                if "text-davinci-002" in data:
                    del data["text-davinci-002"]
                if "text-davinci-003" in data:
                    data["text-davinci-003"].id = "gpt-3.5-turbo-instruct"
                    data["text-davinci-003"].name = "gpt-3.5-turbo-instruct"
                    if "llama_index" in data["text-davinci-003"].mode:
                        data["text-davinci-003"].mode.remove("llama_index")
                    if len(data["text-davinci-003"].langchain["args"]) > 0:
                        if data["text-davinci-003"].langchain["args"][0]["name"] == "model_name":
                            data["text-davinci-003"].langchain["args"][0]["value"] = "gpt-3.5-turbo-instruct"
                    data["text-davinci-003"].llama_index["args"] = []
                    data["text-davinci-003"].llama_index["env"] = []
                    data["text-davinci-003"].llama_index["provider"] = None
                    # replace "text-davinci-003" with "gpt-3.5-turbo-instruct"
                    if "gpt-3.5-turbo-instruct" not in data:
                        data["gpt-3.5-turbo-instruct"] = data["text-davinci-003"]
                        del data["text-davinci-003"]
                updated = True

            # < 2.0.123  <--- update names to models IDs
            if old < parse_version("2.0.123"):
                print("Migrating models from < 2.0.123...")
                if "gpt-4-1106-preview" in data:
                    data["gpt-4-1106-preview"].name = "gpt-4-1106-preview"
                if "gpt-4-vision-preview" in data:
                    data["gpt-4-vision-preview"].name = "gpt-4-vision-preview"
                updated = True

            # < 2.0.134  <--- add agent mode
            if old < parse_version("2.0.134"):
                print("Migrating models from < 2.0.134...")
                exclude = ["gpt-3.5-turbo-instruct", "gpt-4-vision-preview"]
                for id in data:
                    model = data[id]
                    if model.id.startswith("gpt-") and model.id not in exclude:
                        if "agent" not in model.mode:
                            model.mode.append("agent")
                updated = True

            # fix typo in gpt-4 turbo preview for llama
            if old < parse_version("2.1.15"):
                print("Migrating models from < 2.1.15...")
                if "gpt-4-turbo-preview" in data:
                    data["gpt-4-turbo-preview"].llama_index["args"] = [
                        {
                            "name": "model",
                            "value": "gpt-4-turbo-preview",
                            "type": "str",
                        }
                    ]
                updated = True

            # add API endpoint
            if old < parse_version("2.1.19"):
                print("Migrating models from < 2.1.19...")
                for id in data:
                    model = data[id]
                    if model.id.startswith("gpt-"):
                        if "env" not in model.llama_index:
                            model.llama_index["env"] = []
                        is_endpoint = False
                        for arg in model.llama_index["env"]:
                            if "OPENAI_API_BASE" in arg["name"]:
                                is_endpoint = True
                                break
                        if not is_endpoint:
                            model.llama_index["env"].append(
                                {
                                    "name": "OPENAI_API_BASE",
                                    "value": "{api_endpoint}",
                                }
                            )
                        if "env" not in model.langchain:
                            model.langchain["env"] = []
                        is_endpoint = False
                        for arg in model.langchain["env"]:
                            if "OPENAI_API_BASE" in arg["name"]:
                                is_endpoint = True
                                break
                        if not is_endpoint:
                            model.langchain["env"].append(
                                {
                                    "name": "OPENAI_API_BASE",
                                    "value": "{api_endpoint}",
                                }
                            )
                updated = True

            if old < parse_version("2.1.45"):
                print("Migrating models from < 2.1.45...")
                # add missing 2024-04-09
                updated = True

            if old < parse_version("2.2.6"):
                print("Migrating models from < 2.2.6...")
                # add missing gpt-4-turbo
                updated = True

            # < 2.2.7  <--- add expert mode
            if old < parse_version("2.2.7"):
                print("Migrating models from < 2.2.7...")
                exclude = ["gpt-3.5-turbo-instruct", "gpt-4-vision-preview"]
                for id in data:
                    model = data[id]
                    if model.id.startswith("gpt-") and model.id not in exclude:
                        if "expert" not in model.mode:
                            model.mode.append("expert")
                updated = True

            # < 2.2.19  <--- add gpt-4o
            if old < parse_version("2.2.19"):
                print("Migrating models from < 2.2.19...")
                # add gpt-4o
                updated = True

            # < 2.2.20  <--- add gpt-4o-mini
            if old < parse_version("2.2.20"):
                print("Migrating models from < 2.2.20...")
                # add gpt-4o-mini
                updated = True

            # < 2.2.22  <--- add Llama index models
            if old < parse_version("2.2.22"):
                print("Migrating models from < 2.2.22...")
                # add Gemini, Claude, Llama3, Mistral and etc.
                updated = True

            # < 2.2.28  <--- add Llama index models
            if old < parse_version("2.2.28"):
                print("Migrating models from < 2.2.28...")
                # add Llama3.1 70b and 405b, mistral-large
                updated = True

            # < 2.2.33  <--- add agent and expert modes
            if old < parse_version("2.2.33"):
                print("Migrating models from < 2.2.33...")
                exclude = ["dall-e-2", "dall-e-3", "gpt-3.5-turbo-instruct"]
                for id in data:
                    model = data[id]
                    if model.id not in exclude:
                        if "agent" not in model.mode:
                            model.mode.append("agent")
                        if "expert" not in model.mode:
                            model.mode.append("expert")
                # change dalle model names
                if "dall-e-2" in data:
                    data["dall-e-2"].name = "dall-e-2"
                if "dall-e-3" in data:
                    data["dall-e-3"].name = "dall-e-3"
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.models.items = data
            self.window.core.models.save()

            # also patch any missing models
            self.window.core.models.patch_missing()

        return updated
