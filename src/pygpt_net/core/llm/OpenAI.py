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

from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI


class OpenAILLM:
    def __init__(self):
        self.id = "openai"

    def completion(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        os.environ['OPENAI_API_KEY'] = config["api_key"]
        os.environ['OPENAI_API_TOKEN'] = config["api_key"]
        llm = OpenAI(**args)
        return llm

    def chat(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        os.environ['OPENAI_API_KEY'] = config["api_key"]
        os.environ['OPENAI_API_TOKEN'] = config["api_key"]
        llm = ChatOpenAI(**args)
        return llm