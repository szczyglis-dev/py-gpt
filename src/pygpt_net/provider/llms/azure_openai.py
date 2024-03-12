#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.13 01:00:00                  #
# ================================================== #

from langchain_openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.llms.azure_openai import AzureOpenAI as LlamaAzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class AzureOpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AzureOpenAILLM, self).__init__(*args, **kwargs)
        self.id = "azure_openai"
        self.type = ["langchain", "llama_index", "embeddings"]

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

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.llama_index)
        return LlamaAzureOpenAI(**args)

    def get_embeddings_model(self, window) -> BaseEmbedding:
        """
        Return provider instance for embeddings

        :param window: window instance
        :return: Embedding provider instance
        """
        config = window.core.config.get("llama.idx.embeddings.args", [])
        args = self.parse_args({
            "args": config,
        })
        return AzureOpenAIEmbedding(**args)
