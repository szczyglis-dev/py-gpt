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

from langchain.chat_models import ChatOllama


class OllamaLLM:
    def __init__(self):
        self.id = "ollama"

    def completion(self, config, options, stream=False):
        return None

    def chat(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        llm = ChatOllama(args)
        return llm