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

from langchain_community.chat_models import ChatOllama

from llama_index.llms.ollama import Ollama
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem
import nest_asyncio


class OllamaLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OllamaLLM, self).__init__(*args, **kwargs)
        self.id = "ollama"
        self.type = ["langchain", "llama_index", "embeddings"]

    def completion(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        return None

    def chat(self, window, model: ModelItem, stream: bool = False):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.langchain)
        return ChatOllama(**args)

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        nest_asyncio.apply()
        args = self.parse_args(model.llama_index)
        return Ollama(**args)

    def get_embeddings_model(self, window, config: list = None) -> BaseEmbedding:
        """
        Return provider instance for embeddings

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            })
        return OllamaEmbedding(**args)
