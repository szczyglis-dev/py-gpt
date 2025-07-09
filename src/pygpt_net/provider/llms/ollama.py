#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.09 22:00:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

# from langchain_community.chat_models import ChatOllama

from .ollama_custom import Ollama

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem
import nest_asyncio


class OllamaLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OllamaLLM, self).__init__(*args, **kwargs)
        self.id = "ollama"
        self.name = "Ollama"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance

        args = self.parse_args(model.langchain)
        if "model" not in args:
            args["model"] = model.id
        return ChatOllama(**args)
        """
        pass

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        nest_asyncio.apply()
        args = self.parse_args(model.llama_index, window)
        if "request_timeout" not in args:
            args["request_timeout"] = 120
        if 'OLLAMA_API_BASE' in os.environ:
            if "base_url" not in args:
                args["base_url"] = os.environ['OLLAMA_API_BASE']
        if "model" not in args:
            args["model"] = model.id
        return Ollama(**args)

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
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
            }, window)
        if 'OLLAMA_API_BASE' in os.environ:
            if "base_url" not in args:
                args["base_url"] = os.environ['OLLAMA_API_BASE']
        return OllamaEmbedding(**args)

    def init_embeddings(
            self,
            window,
            env: Optional[List[Dict]] = None
    ):
        """
        Initialize embeddings provider

        :param window: window instance
        :param env: ENV configuration list
        """
        super(OllamaLLM, self).init_embeddings(window, env)

        # === FIX FOR LOCAL EMBEDDINGS ===
        # if there is no OpenAI api key then set fake key to prevent empty key Llama-index error
        if ('OPENAI_API_KEY' not in os.environ
                and (window.core.config.get('api_key') is None or window.core.config.get('api_key') == "")):
            os.environ['OPENAI_API_KEY'] = "_"
