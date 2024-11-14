#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.mode = "step"  # step|plan

    def get_mode(self) -> str:
        """
        Return Agent mode

        :return: Agent mode
        """
        return self.mode

    def get_agent(self, window, kwargs: dict):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        pass