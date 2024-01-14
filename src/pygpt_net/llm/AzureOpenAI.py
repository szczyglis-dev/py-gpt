#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.14 11:00:00                  #
# ================================================== #

from langchain_community.llms import AzureOpenAI
from langchain_openai import AzureChatOpenAI

from .base import BaseLLM
from pygpt_net.item.model import ModelItem


class AzureOpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AzureOpenAILLM, self).__init__(*args, **kwargs)
        self.id = "azure_openai"
        self.type = ["langchain"]

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
