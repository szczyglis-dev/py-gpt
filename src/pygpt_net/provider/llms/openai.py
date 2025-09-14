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

# from langchain_openai import OpenAI
# from langchain_openai import ChatOpenAI

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from llama_index.multi_modal_llms.openai import OpenAIMultiModal as LlamaOpenAIMultiModal

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_CHAT,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class OpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OpenAILLM, self).__init__(*args, **kwargs)
        self.id = "openai"
        self.name = "OpenAI"
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

        args = self.parse_args(model.langchain)
        if "model" not in args:
            args["model"] = model.id
        return OpenAI(**args)
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
        return ChatOpenAI(**args)
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
        from .llama_index.openai import OpenAI as LlamaOpenAI
        from .llama_index.openai import OpenAIResponses as LlamaOpenAIResponses
        args = self.parse_args(model.llama_index, window)
        if "api_key" not in args:
            args["api_key"] = window.core.config.get("api_key", "")
        if "model" not in args:
            args["model"] = model.id

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        if window.core.config.get('api_use_responses_llama', False):
            tools = []
            tools = window.core.api.openai.remote_tools.append_to_tools(
                mode=MODE_LLAMA_INDEX,
                model=model,
                stream=stream,
                is_expert_call=False,
                tools=tools,
            )
            if tools:
                args["built_in_tools"] = tools
            return LlamaOpenAIResponses(**args)
        else:
            return LlamaOpenAI(**args)

    def llama_multimodal(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaMultiModalLLM:
        """
        Return multimodal LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        return LlamaOpenAIMultiModal(**args)

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
        from llama_index.embeddings.openai import OpenAIEmbedding
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        if "api_key" not in args:
            args["api_key"] = window.core.config.get("api_key", "")
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAIEmbedding(**args)

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
        client = self.get_client(window)
        models_list = client.models.list()
        if models_list.data:
            for item in models_list.data:
                items.append({
                    "id": item.id,
                    "name": item.id,
                })
        return items