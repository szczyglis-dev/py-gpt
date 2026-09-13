#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:48:00
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
from pygpt_net.core.types.reasoning import get_google_thinking_kwargs


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

    @staticmethod
    def _generation_config_dict(value) -> dict:
        """Normalize a Google GenerateContentConfig/dict for safe merging."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        try:
            return value.model_dump(exclude_none=True)
        except Exception:
            return {}

    def _append_reasoning_effort(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if not effort:
            return
        thinking = get_google_thinking_kwargs(model.id, effort)
        if not thinking:
            return
        generation_config = self._generation_config_dict(args.get("generation_config"))
        # llama-index-llms-google-genai 0.11.1 expects a typed
        # GenerateContentConfig here and calls .model_dump() on it internally.
        generation_config["thinking_config"] = gtypes.ThinkingConfig(**thinking)
        args["generation_config"] = gtypes.GenerateContentConfig(**generation_config)

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return LlamaIndex completion provider without server-side chat tools."""
        return self.llama(
            window=window,
            model=model,
            stream=stream,
            remote_tools=False,
        )

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from pygpt_net.provider.llms.google_capture import PyGPTGoogleGenAI
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_google", "")

        window.core.api.google.setup_env()  # setup VertexAI if configured
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        had_generation_config = "generation_config" in args
        self._append_reasoning_effort(window, model, args)

        # -----------------------------------------------------------
        # Remote built-in tools for Google GenAI via LlamaIndex:
        # - Google Search grounding (Tool(google_search=GoogleSearch()))
        # - Code Execution (Tool(code_execution=ToolCodeExecution()))
        # - Url Context (Tool(url_context=UrlContext)) on 2.x+
        # We reuse native builder and forward tools into LlamaIndex.
        # If 1 tool -> use 'built_in_tool', if >1 -> pack into generation_config.tools
        # -----------------------------------------------------------
        built_tools = []
        if remote_tools:
            try:
                built_tools = window.core.api.google.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                window.core.debug.log(e)

        if built_tools and not had_generation_config:
            # A runtime thinking_config may have created generation_config after
            # parsing the model args.  It must not suppress remote tools.  A
            # user-supplied generation_config keeps the historical behavior.
            if len(built_tools) == 1:
                if "built_in_tool" not in args:
                    args["built_in_tool"] = built_tools[0]
            else:
                generation_config = self._generation_config_dict(args.get("generation_config"))
                if not generation_config.get("tools"):
                    generation_config["tools"] = built_tools
                    args["generation_config"] = gtypes.GenerateContentConfig(**generation_config)

        # The pinned llama-index Google integration treats generation_config as
        # a pydantic model, not a plain dict. Normalize user/model args too.
        if isinstance(args.get("generation_config"), dict):
            args["generation_config"] = gtypes.GenerateContentConfig(**args["generation_config"])

        return PyGPTGoogleGenAI(**args, pygpt_remote_tools=built_tools)

    def llama_chat_with_files(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
    ) -> LlamaBaseLLM:
        """Use the shared provider continuation adapter when Computer Use is active."""
        remote = window.core.api.google.remote_tools
        if remote.is_computer_use_enabled(model):
            llm = self.llama_agent(
                window=window,
                model=model,
                stream=stream,
                allow_remote_tools=True,
            )
            binder = getattr(llm, "bind_computer_runtime", None)
            if callable(binder):
                binder(computer_runtime)
            return llm
        return self.llama(window=window, model=model, stream=stream)

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """Return Google GenAI configured for Agents v2.

        Remote Google tools are merged with FunctionAgent tools at request time
        by the adapter, and grounding URLs are collected for PyGPT artifacts.
        """
        from pygpt_net.provider.llms.google_agent import AgentGoogleGenAI

        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_google", "")

        window.core.api.google.setup_env()
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self._append_reasoning_effort(window, model, args)

        remote = []
        if allow_remote_tools:
            try:
                remote = window.core.api.google.remote_tools.build_remote_tools(model=model) or []
            except Exception as e:
                window.core.debug.log(e)

        if isinstance(args.get("generation_config"), dict):
            args["generation_config"] = gtypes.GenerateContentConfig(**args["generation_config"])

        return AgentGoogleGenAI(
            **args,
            pygpt_remote_tools=remote,
        )

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
        try:
            client = window.core.api.google.get_client()
            models_list = client.models.list()
            for item in models_list:
                id = item.name.replace("models/", "")
                items.append({
                    "id": id,
                    "name": id,  # TODO: token limit get from API
                })
        except Exception as e:
            window.core.debug.log(e)
        return items

    def inject_llamaindex_http_clients(self, args: dict, cfg) -> dict:
        proxy = cfg.get("api_proxy")
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        if proxy:
            http_options = gtypes.HttpOptions(
                client_args={"proxy": proxy},
                async_client_args={"proxy": proxy},
            )
            args["http_options"] = http_options
        return args
