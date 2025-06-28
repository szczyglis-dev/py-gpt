#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

from typing import Optional, List, Dict


class LLM:
    def __init__(self, window=None):
        """
        LLMs manager

        :param window: Window instance
        """
        self.window = window
        self.llms = {}

    def get_ids(
            self,
            type: Optional[str] = None
    ) -> List[str]:
        """
        Get providers ids

        :param type: provider type
        :return: providers ids
        """
        if type is not None:
            return [id for id in self.llms.keys() if type in self.llms[id].type]
        return list(self.llms.keys())  # get all

    def get_choices(
            self,
            type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get providers choices

        :param type: provider type
        :return: providers choices
        """
        choices = {}
        if type is not None:
            for id in list(self.llms.keys()):
                if type in self.llms[id].type:
                    choices[id] = self.llms[id].name
        else:
            for id in list(self.llms.keys()):
                choices[id] = self.llms[id].name

        # sorted by name
        return dict(sorted(choices.items(), key=lambda item: item[1].lower()))

    def register(
            self,
            id: str,
            llm
    ):
        """
        Register LLM provider

        :param id: LLM id
        :param llm: LLM object
        """
        self.llms[id] = llm
