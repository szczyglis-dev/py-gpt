#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 10:00:00                  #
# ================================================== #

class Placeholder:
    def __init__(self, window=None):
        """
        Configuration placeholder options controller

        :param window: Window instance
        """
        self.window = window

    def apply(self, option: dict):
        """
        Apply placeholders to option

        :param option: Option dict
        """
        if option['type'] == 'dict' and 'keys' in option:
            for key in option['keys']:
                item = option['keys'][key]
                if type(item) is dict:
                    if "type" in item:
                        if item["type"] == "combo":
                            if "use" in item:
                                item["keys"] = self.apply_by_id(item["use"])
        elif option['type'] == 'combo':
            if "use" in option:
                option["keys"] = self.apply_by_id(option["use"])

    def apply_by_id(self, id: str) -> list:
        """
        Apply placeholders by id

        :param id: Placeholder options id
        """
        if id == "presets":
            return self.get_presets()
        elif id == "models":
            return self.get_models()
        elif id == "langchain_providers":
            return self.get_langchain_providers()
        elif id == "llama_index_providers":
            return self.get_llama_index_providers()
        elif id == "vector_storage":
            return self.get_vector_storage()
        elif id == "var_types":
            return self.get_var_types()
        else:
            return []

    def get_langchain_providers(self) -> list:
        """
        Get langchain placeholders list

        :return: placeholders list
        """
        ids = self.window.core.llm.get_ids("langchain")
        data = []
        data.append({'_': '---'})
        for id in ids:
            data.append({id: id})
        return data

    def get_llama_index_providers(self) -> list:
        """
        Get langchain placeholders list

        :return: placeholders list
        """
        ids = self.window.core.llm.get_ids("llama_index")
        data = []
        data.append({'_': '---'})
        for id in ids:
            data.append({id: id})
        return data

    def get_vector_storage(self) -> list:
        """
        Get vector storage placeholders list

        :return: placeholders list
        """
        ids = self.window.core.idx.storage.get_ids()
        data = []
        data.append({'_': '---'})
        for id in ids:
            data.append({id: id})
        return data

    def get_var_types(self) -> list:
        """
        Get langchain placeholders list

        :return: placeholders list
        """
        types = ['str', 'int', 'float', 'bool', 'dict', 'list', 'None']
        data = []
        for type in types:
            data.append({type: type})
        return data

    def get_presets(self) -> list:
        """
        Get presets placeholders list

        :return: Presets placeholders list
        """
        presets = self.window.core.presets.get_all()
        data = []
        data.append({'_': '---'})
        for id in presets:
            if id.startswith("current."):  # ignore "current" preset
                continue
            data.append({id: id})  # TODO: name
        return data

    def get_models(self) -> list:
        """
        Get models placeholders list

        :return: Models placeholders list
        """
        models = self.window.core.models.get_all()
        data = []
        data.append({'_': '---'})
        for id in models:
            data.append({id: id})  # TODO: name
        return data
