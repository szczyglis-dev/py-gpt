#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:55:00                  #
# ================================================== #

import os.path
from typing import Optional, Union, List, Dict

from llama_index.core.llms.llm import BaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.llms.openai import OpenAI

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODEL_DEFAULT_MINI, MODE_CHAT, MODE_COMPLETION,
)
from pygpt_net.item.model import ModelItem


class Llm:
    def __init__(self, window=None):
        """
        LLM provider core

        :param window: Window instance
        """
        self.window = window
        self.default_model = MODEL_DEFAULT_MINI
        self.default_embed = "openai"
        self.initialized = False

    def init(self):
        """Init base ENV vars"""
        os.environ['OPENAI_API_KEY'] = str(self.window.core.config.get('api_key'))
        os.environ['OPENAI_API_BASE'] = str(self.window.core.config.get('api_endpoint'))
        os.environ['OPENAI_ORGANIZATION'] = str(self.window.core.config.get('organization_key'))

    def get(
            self,
            model: Optional[ModelItem] = None,
            multimodal: bool = False,
            stream: bool = False,
            computer_runtime=None,
    ) -> Union[BaseLLM, MultiModalLLM]:
        """
        Get LLM provider

        :param model: Model item
        :param multimodal: Allow multi-modal flag (True to get multimodal provider if available)
        :param stream: Stream mode (True to enable streaming)
        :param computer_runtime: Shared provider-native Computer Use runtime adapter
        :return: Llama LLM instance
        """
        # TMP: deprecation warning fix
        # https://github.com/DataDog/dd-trace-py/issues/8212#issuecomment-1971063988
        if not self.initialized:
            # import warnings
            # from langchain._api import LangChainDeprecationWarning
            # warnings.simplefilter("ignore", category=LangChainDeprecationWarning)
            self.initialized = True

        llm = None
        if model is not None:
            provider = model.get_provider()
            llm_provider = self.window.core.llm.get(provider)
            if llm_provider is not None:
                # init env vars
                llm_provider.init(
                    window=self.window,
                    model=model,
                    mode=MODE_LLAMA_INDEX,
                    sub_mode="",
                )
                # Some LlamaIndex callers need a provider-owned client-side
                # continuation loop for native Computer Use. Keep this opt-in so
                # all other callers retain the regular provider.
                if computer_runtime is not None:
                    runtime = computer_runtime
                    runtime_for_model = getattr(computer_runtime, "for_model", None)
                    if callable(runtime_for_model):
                        runtime = runtime_for_model(model)
                    llm = llm_provider.llama_with_computer_runtime(
                        window=self.window,
                        model=model,
                        stream=stream,
                        computer_runtime=runtime,
                    )
                else:
                    llm = llm_provider.llama(
                        window=self.window,
                        model=model,
                        stream=stream,
                    )
            elif self.window.core.llm.is_custom_provider(provider):
                raise RuntimeError(f"Custom provider is not configured: {provider}")

        # default model
        if llm is None:
            self.init()  # init env vars
            llm = OpenAI(
                temperature=0.0,
                model=self.default_model,
            )
        return llm

    def get_completion(
            self,
            model: Optional[ModelItem] = None,
            stream: bool = False,
    ) -> BaseLLM:
        """Return a LlamaIndex provider configured for plain-text completion."""
        if not self.initialized:
            self.initialized = True

        llm = None
        if model is not None:
            provider = model.get_provider()
            llm_provider = self.window.core.llm.get(provider)
            if llm_provider is not None:
                llm_provider.init(
                    window=self.window,
                    model=model,
                    mode=MODE_LLAMA_INDEX,
                    sub_mode=MODE_COMPLETION,
                )
                llm = llm_provider.llama_completion(
                    window=self.window,
                    model=model,
                    stream=stream,
                )
            elif self.window.core.llm.is_custom_provider(provider):
                raise RuntimeError(f"Custom provider is not configured: {provider}")

        if llm is None:
            raise RuntimeError("LlamaIndex completion provider is not configured")
        return llm

    def get_agent(
            self,
            model: Optional[ModelItem] = None,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> BaseLLM:
        """
        Get a LlamaIndex LLM configured for Agents v2.

        This path lets each provider attach its native/server-side remote tools
        directly to the LLM request while keeping the regular LlamaIndex path
        unchanged.

        :param model: Model item
        :param stream: Stream mode
        :param allow_remote_tools: Allow provider-native remote tools
        :return: LlamaIndex LLM instance
        """
        if not self.initialized:
            self.initialized = True

        llm = None
        if model is not None:
            provider = model.get_provider()
            llm_provider = self.window.core.llm.get(provider)
            if llm_provider is not None:
                # LlamaIndex provider settings/env are still the source of the
                # model credentials for Agents v2.
                llm_provider.init(
                    window=self.window,
                    model=model,
                    mode=MODE_LLAMA_INDEX,
                    sub_mode="",
                )
                llm = llm_provider.llama_agent(
                    window=self.window,
                    model=model,
                    stream=stream,
                    allow_remote_tools=allow_remote_tools,
                )
            elif self.window.core.llm.is_custom_provider(provider):
                raise RuntimeError(f"Custom provider is not configured: {provider}")

        if llm is None:
            self.init()
            llm = OpenAI(
                temperature=0.0,
                model=self.default_model,
            )
        return llm

    def get_embeddings_provider(self) -> BaseEmbedding:
        """
        Get current embeddings provider

        :return: Llama embeddings provider instance
        """
        provider = self.window.core.config.get("llama.idx.embeddings.provider", self.default_embed)
        env = self.window.core.config.get("llama.idx.embeddings.env", [])
        args = self.window.core.config.get("llama.idx.embeddings.args", [])

        llm_provider = self.window.core.llm.get(provider) if provider is not None else None
        if llm_provider is None:
            provider = self.default_embed
            llm_provider = self.window.core.llm.get(provider)

        llm_provider.init_embeddings(
            window=self.window,
            env=env,
        )
        model_name = self.extract_model_name_from_args(args)
        self.window.core.idx.log(f"Embeddings: using global provider: {provider}, model_name: {model_name}")
        return llm_provider.get_embeddings_model(
            window=self.window,
            config=args,
        )

    def get_service_context(
            self,
            model: Optional[ModelItem] = None,
            stream: bool = False,
            auto_embed: bool = False,
            computer_runtime=None,
    ):
        """
        Get service context + embeddings provider

        :param model: Model item (for query)
        :param stream: Stream mode (True to enable streaming)
        :param auto_embed: Auto-detect embeddings provider based on model capabilities
        :param computer_runtime: Shared provider-native Computer Use runtime adapter
        :return: Service context instance
        """
        llm = self.get(model=model, stream=stream, computer_runtime=computer_runtime)
        if not auto_embed:
            embed_model = self.get_embeddings_provider()
        else:
            embed_model = self.get_custom_embed_provider(model=model)
        return llm, embed_model


    def get_custom_embed_provider(self, model: Optional[ModelItem] = None) -> Optional[BaseEmbedding]:
        """
        Get custom embeddings provider based on model

        :param model: Model item
        :return: Embeddings provider instance or None
        """
        # base_embedding_provider = self.window.core.config.get("llama.idx.embeddings.provider", self.default_embed)
        # if base_embedding_provider == model.provider:
            # return self.get_embeddings_provider()

        embed_model = None
        args = []

        # try to get custom args from config for the model provider
        is_custom_provider = False
        defaults = self.window.core.config.get("llama.idx.embeddings.default", [])
        for item in defaults:
            provider = item.get("provider", "")
            if provider and provider == model.provider:
                is_custom_provider = True
                client_args = self.window.core.models.prepare_client_args(MODE_CHAT, model)
                model_name = item.get("model", "")
                if not model_name:
                    model_name = model.id  # fallback to model id if not set in config (Ollama, etc)
                args = [
                    {
                        "name": "model_name",
                        "type": "str",
                        "value": model_name,
                    }
                ]
                if model.provider != "ollama":
                    args.append(
                        {
                            "name": "api_key",
                            "type": "str",
                            "value": client_args.get("api_key", ""),
                        }
                    )
                if model.provider == "local_ai":
                    custom_api_endpoint = (getattr(model, "custom_api_endpoint", "") or "").strip()
                    if custom_api_endpoint:
                        args.append(
                            {
                                "name": "api_base",
                                "type": "str",
                                "value": custom_api_endpoint,
                            }
                        )
                self.window.core.idx.log(f"Embeddings: trying to use {model.provider}, model_name: {model_name}")
                break

        if is_custom_provider:
            llm_provider = self.window.core.llm.get(model.provider)
            if llm_provider is not None:
                embed_model = llm_provider.get_embeddings_model(
                    window=self.window,
                    config=args,
                )
        if not embed_model:
            self.window.core.idx.log(f"Embeddings: not configured for {model.provider}. Fallback: using global provider.")
            embed_model = self.get_embeddings_provider()
        return embed_model

    def extract_model_name_from_args(self, args: List[Dict]) -> str:
        """
        Extract model name from provider args

        :param args: List of args
        :return: Model name if configured
        """
        model_name = ""
        for item in args:
            if item.get("name") in ["model", "model_name"]:
                model_name = item.get("value")
                break
        return model_name
