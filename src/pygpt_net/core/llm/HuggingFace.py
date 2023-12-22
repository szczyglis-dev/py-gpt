#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.06 12:00:00                  #
# ================================================== #
import os

from langchain.llms import HuggingFaceHub


class HuggingFaceLLM:
    def __init__(self):
        self.id = "huggingface"

    def completion(self, config, options, stream=False):
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
        os.environ['HUGGINGFACEHUB_API_TOKEN'] = options['api_key']
        os.environ['HUGGINGFACEHUB_API_KEY'] = options['api_key']
        llm = HuggingFaceHub(**args)
        return llm

    def chat(self, config, options, stream=False):
        """
        Return LLM model for chat

        :param config: Config instance
        :param options: options dict
        :param stream: stream mode
        :return: LLM model
        """
        return None
