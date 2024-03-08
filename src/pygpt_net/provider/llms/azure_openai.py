#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.08 23:00:00                  #
# ================================================== #

from langchain_openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI
from llama_index.llms.azure_openai import AzureOpenAI as LlamaAzureOpenAI

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class AzureOpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AzureOpenAILLM, self).__init__(*args, **kwargs)
        self.id = "azure_openai"
        self.type = ["langchain", "llama_index"]

    def completion(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.langchain)
        return AzureOpenAI(**args)

    def chat(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.langchain)
        return AzureChatOpenAI(**args)

    def llama(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.llama_index)
        return LlamaAzureOpenAI(**args)
