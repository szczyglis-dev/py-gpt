#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 16:00:00                  #
# ================================================== #

from llama_index.llms.gemini import Gemini

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class GoogleLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(GoogleLLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - GOOGLE_API_KEY - API key for Google API
        Required args:
            - model: model name, e.g. gemini-1,5-pro
            - api_key: API key for Google API
        """
        self.id = "google"
        self.type = ["llama_index"]

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.llama_index)
        return Gemini(**args)
