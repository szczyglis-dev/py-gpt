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
                                if item["use"] == "presets":
                                    item["keys"] = self.get_presets()
                                elif item["use"] == "models":
                                    item["keys"] = self.get_models()
        elif option['type'] == 'combo':
            if "use" in option:
                if option["use"] == "presets":
                    option["keys"] = self.get_presets()
                elif option["use"] == "models":
                    option["keys"] = self.get_models()

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
