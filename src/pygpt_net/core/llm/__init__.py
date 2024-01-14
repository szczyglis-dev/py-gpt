#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.14 04:00:00                  #
# ================================================== #

class LLM:
    def __init__(self, window=None):
        """
        LLMs manager

        :param window: Window instance
        """
        self.window = window
        self.llms = {}

    def get_ids(self, type: str = None) -> list:
        """
        Get providers ids

        :param type: provider type
        :return: providers ids
        """
        if type is not None:
            return [id for id in self.llms.keys() if type in self.llms[id].type]
        return list(self.llms.keys())

    def register(self, id: str, llm):
        """
        Register LLM provider

        :param id: LLM id
        :param llm: LLM object
        """
        self.llms[id] = llm
