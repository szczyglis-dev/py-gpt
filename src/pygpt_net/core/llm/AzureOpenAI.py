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
from langchain.llms import AzureOpenAI
from langchain.chat_models import AzureChatOpenAI


class AzureOpenAILLM:
    def __init__(self):
        self.id = "azure_openai"

    def completion(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        os.environ['OPENAI_API_KEY'] = config["api_key"]
        os.environ['OPENAI_API_TOKEN'] = config["api_key"]
        llm = AzureOpenAI(**args)
        return llm

    def chat(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        os.environ['OPENAI_API_KEY'] = config["api_key"]
        os.environ['OPENAI_API_TOKEN'] = config["api_key"]
        llm = AzureChatOpenAI(**args)
        return llm