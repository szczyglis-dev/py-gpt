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

from langchain_community.llms import HuggingFaceTextGenInference
from langchain_experimental.chat_models import Llama2Chat


class Llama2LLM:
    def __init__(self):
        self.id = "llama2"

    def completion(self, config, options: dict, stream: bool = False):
        """
        Return LLM model for completion

        :param config: Config instance
        :param options: options dict
        :param stream: stream mode
        :return: LLM model
        """
        return None

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
        textgen = HuggingFaceTextGenInference(args)
        llm = Llama2Chat(llm=textgen)
        return llm
