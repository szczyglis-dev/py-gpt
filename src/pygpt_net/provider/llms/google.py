#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 01:00:00                  #
# ================================================== #

from typing import Optional, List, Dict

from google.genai import types as gtypes
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

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
        from llama_index.llms.google_genai import GoogleGenAI
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_google", "")

        window.core.api.google.setup_env()  # setup VertexAI if configured
        args = self.inject_llamaindex_http_clients(args, window.core.config)
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
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_google", "")
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        window.core.api.google.setup_env()  # setup VertexAI if configured
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return GoogleGenAIEmbedding(**args)

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return list of models for the provider

        :param window: window instance
        :return: list of models
        """
        items = []
        client = window.core.api.google.get_client()
        models_list = client.models.list()
        for item in models_list:
            id = item.name.replace("models/", "")
            items.append({
                "id": id,
                "name": id,  # TODO: token limit get from API
            })
        return items

    def inject_llamaindex_http_clients(self, args: dict, cfg) -> dict:
        proxy = cfg.get("api_proxy")
        if proxy:
            http_options = gtypes.HttpOptions(
                client_args={"proxy": proxy},
                async_client_args={"proxy": proxy},
            )
            args["http_options"] = http_options
        return args
