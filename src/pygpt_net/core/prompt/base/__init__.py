#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.02.01 11:00:00                  #
# ================================================== #

from pygpt_net.item.model import ModelItem
from .gpt import Gpt

class Base:
    def __init__(self, window=None):
        """
        Base prompt templates

        :param window: Window instance
        """
        self.window = window
        self.providers = {
            "gpt" : Gpt(window)
        }
        self.model_prompts = [
            "cmd",
            "cmd.extra",
            "cmd.extra.assistants",
        ]

    def get(
            self,
            prompt: str,
            mode: str = None,
            model: ModelItem = None
    ) -> str:
        """
        Get system prompt content

        CMD/TOOL EXECUTE prompts:
         - cmd
         - cmd.extra
         - cmd.extra.assistants

        :param prompt: id of the prompt
        :param mode: mode
        :param model: model item
        :return: text content
        """
        return self.get_db(prompt, mode, model)  # from db

    def get_db(
            self,
            prompt: str,
            mode: str = None,
            model: ModelItem = None
    ) -> str:
        """
        Get system prompt content from database

        :param prompt: id of the prompt
        :param mode: mode
        :param model: model item
        :return: text content
        """
        key = "prompt." + prompt
        if self.window.core.config.has(key):
            return str(self.window.core.config.get(key))
        return ""