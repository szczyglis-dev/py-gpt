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

from langchain.llms import HuggingFaceTextGenInference
from langchain_experimental.chat_models import Llama2Chat


class Llama2LLM:
    def __init__(self):
        self.id = "llama2"

    def completion(self, config, options, stream=False):
        return None

    def chat(self, config, options, stream=False):
        args = {}
        if 'args' in options:
            args = options['args']
        textgen = HuggingFaceTextGenInference(args)
        llm = Llama2Chat(llm=textgen)
        return llm