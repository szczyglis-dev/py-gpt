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

import os

from langchain_community.llms import Anthropic
from langchain_community.chat_models import ChatAnthropic


class AnthropicLLM:
    def __init__(self):
        self.id = "anthropic"

    def completion(self, config, options: dict, stream: bool = False):
        """
        Return LLM model for completion

        :param config: Config instance
        :param options: options dict
        :param stream: stream mode
        :return: LLM model
        """
        args = {}
        if 'args' in options:
            args = options['args']
        llm = Anthropic(**args)
        return llm

    def chat(self, config, options: dict, stream: bool = False):
        """
        Return LLM model for chat

        :param config: Config instance
        :param options: options dict
        :param stream: stream mode
        :return: LLM model
        """
        args = {}
        if 'args' in options:
            args = options['args']
        llm = ChatAnthropic(**args)
        return llm
