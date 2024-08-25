#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #


class Common:
    def __init__(self, window=None):
        """
        Idx common controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Set up UI"""
        pass

    def get_loaders_choices(self) -> list:
        """
        Get available loaders choices

        Prefixes:
            file_ - file loader
            web_ - web loader
            online_ - online loader

        :return: list of available loaders
        """
        data = []

        # offline (built-in)
        loaders = self.window.core.idx.indexing.get_data_providers()
        for id in loaders:
            loader = loaders[id]
            # file
            if "file" in loader.type:
                id = "file_" + id
                ext_str = ""
                if loader.extensions:
                    ext_str = " (" + ", ".join(loader.extensions) + ")"
                # name = "(File) " + loader.name + ext_str  # TODO: implement option names
                data.append({
                    id: id
                })
            # web
            if "web" in loader.type:
                id = "web_" + id
                # name = "(Web) " + loader.name  # TODO: implement option names
                data.append({
                    id: id
                })
        return data
