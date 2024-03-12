#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 21:00:00                  #
# ================================================== #

from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class OpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OpenAILLM, self).__init__(*args, **kwargs)
        self.id = "openai"
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
        return OpenAI(**args)

    def chat(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.langchain)
        return ChatOpenAI(**args)

    def llama(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.llama_index)
        return LlamaOpenAI(**args)

    def get_embeddings_model(self, window):
        """
        Return provider instance for embeddings

        :param window: window instance
        :return: Embedding provider instance
        """
        config = window.core.config.get("llama.idx.embeddings.args", {})
        args = self.parse_args({
            "args": config,
        })
        return OpenAIEmbedding(**args)
