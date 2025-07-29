#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

import json

from pygpt_net.item.model import ModelItem


class Tools:
    def __init__(self, window=None):
        """
        Chat wrapper

        :param window: Window instance
        """
        self.window = window

    def prepare(
            self,
            model: ModelItem,
            functions: list
    ) -> list:
        """
        Prepare tools for the model (ChatCompletions API)

        :param model: Model item
        :param functions: List of functions
        :return: List of tools
        """
        tools = []
        if functions is not None and isinstance(functions, list):
            for function in functions:
                if str(function['name']).strip() == '' or function['name'] is None:
                    continue
                params = {}
                if function['params'] is not None and function['params'] != "":
                    params = json.loads(function['params'])  # unpack JSON from string

                    # Google API fix:
                    if model.provider == "google":
                        if "properties" in params:
                            for k, v in params["properties"].items():
                                if "type" in v and v["type"] != "string":
                                    if "enum" in v:
                                        del v["enum"]

                tools.append({
                    "type": "function",
                    "function": {
                        "name": function['name'],
                        "parameters": params,
                        "description": function['desc'],
                    }
                })
        return tools

    def prepare_responses_api(
            self,
            model: ModelItem,
            functions: list
    ) -> list:
        """
        Prepare tools for the model (Responses API)

        :param model: Model item
        :param functions: List of functions
        :return: List of tools
        """
        tools = []
        if functions is not None and isinstance(functions, list):
            for function in functions:
                if str(function['name']).strip() == '' or function['name'] is None:
                    continue
                params = {}
                if function['params'] is not None and function['params'] != "":
                    params = json.loads(function['params'])  # unpack JSON from string
                tools.append({
                    "type": "function",
                    "name": function['name'],
                    "parameters": params,
                    "description": function['desc'],
                })
        return tools