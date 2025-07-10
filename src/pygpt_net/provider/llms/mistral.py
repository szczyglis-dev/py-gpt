#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 01:00:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from llama_index.llms.mistralai import MistralAI
from llama_index.embeddings.mistralai import MistralAIEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class MistralAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(MistralAILLM, self).__init__(*args, **kwargs)
        self.id = "mistral_ai"
        self.name = "Mistral AI"
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
        return MistralAI(**args)

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
        return MistralAIEmbedding(**args)

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
        super(MistralAILLM, self).init_embeddings(window, env)

        # === FIX FOR LOCAL EMBEDDINGS ===
        # if there is no OpenAI api key then set fake key to prevent empty key Llama-index error
        if ('OPENAI_API_KEY' not in os.environ
                and (window.core.config.get('api_key') is None or window.core.config.get('api_key') == "")):
            os.environ['OPENAI_API_KEY'] = "_"
