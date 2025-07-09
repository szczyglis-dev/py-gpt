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

from typing import Optional, List, Dict

from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.gemini import GeminiEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
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
        self.name = "Google"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

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
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        return GoogleGenAI(**args)

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
        return GeminiEmbedding(**args)
