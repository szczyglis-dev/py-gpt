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

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class AzureOpenAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AzureOpenAILLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - AZURE_OPENAI_API_KEY - API key for Azure OpenAI API
            - AZURE_OPENAI_ENDPOINT - API endpoint for Azure OpenAI API
        Required args:
            - model: model name, e.g. gpt-4
            - api_key: API key for Azure OpenAI API
        """
        self.id = "azure_openai"
        self.name = "Azure OpenAI"
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
        return AzureOpenAI(**args)
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
        return AzureChatOpenAI(**args)
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
        from llama_index.llms.azure_openai import AzureOpenAI as LlamaAzureOpenAI
        args = self.parse_args(model.llama_index, window)
        env = (model.llama_index or {}).get("env", [])
        if not args.get("api_key"):
            args["api_key"] = (
                self.get_env_override(window, env, ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"])
                or window.core.config.get("api_key", "")
            )
        if not args.get("model"):
            args["model"] = model.id
        if not args.get("azure_endpoint"):
            endpoint = (
                self.get_env_override(window, env, ["AZURE_OPENAI_ENDPOINT"])
                or window.core.config.get("api_azure_endpoint", "")
            )
            if endpoint:
                args["azure_endpoint"] = endpoint
        if not args.get("api_version"):
            api_version = (
                self.get_env_override(window, env, ["OPENAI_API_VERSION", "AZURE_OPENAI_API_VERSION"])
                or window.core.config.get("api_azure_version", "")
            )
            if api_version:
                args["api_version"] = api_version
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "LlamaAzureOpenAI")
        return LlamaAzureOpenAI(**args)

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
        from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        env = window.core.config.get("llama.idx.embeddings.env", []) or []
        if not args.get("api_key"):
            args["api_key"] = (
                self.get_env_override(window, env, ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"])
                or window.core.config.get("api_key", "")
            )
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")
        if not args.get("azure_endpoint"):
            endpoint = (
                self.get_env_override(window, env, ["AZURE_OPENAI_ENDPOINT"])
                or window.core.config.get("api_azure_endpoint", "")
            )
            if endpoint:
                args["azure_endpoint"] = endpoint
        if not args.get("api_version"):
            api_version = (
                self.get_env_override(window, env, ["OPENAI_API_VERSION", "AZURE_OPENAI_API_VERSION"])
                or window.core.config.get("api_azure_version", "")
            )
            if api_version:
                args["api_version"] = api_version
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        return AzureOpenAIEmbedding(**args)
