#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_EMBEDDINGS,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem

from .agents import GoogleAgents
from .parameters import GoogleParameters, google_types



class GoogleLLM(BaseLLM):
    agents_class = GoogleAgents

    def __init__(self, *args, **kwargs):
        super(GoogleLLM, self).__init__(*args, **kwargs)
        """
        Required ENV variables:
            - GOOGLE_API_KEY - API key for Google API
        Required args:
            - model: model name, e.g. gemini-1.5-pro
            - api_key: API key for Google API
        """
        self.parameters = GoogleParameters(self)
        self.id = "google"
        self.name = "Google"
        self.type = [MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        from .config import setup
        return setup()

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex chat provider

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :param remote_tools: enable remote tools for Google GenAI
        :return: LLM provider instance
        """
        from .capture import PyGPTGoogleGenAI
        args = self.parameters.prepare(window, model)
        had_generation_config = "generation_config" in args
        self.parameters.reasoning(window, model, args)

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
                generation_config = self.parameters.generation_config(args.get("generation_config"))
                if not generation_config.get("tools"):
                    generation_config["tools"] = built_tools
                    args["generation_config"] = google_types().GenerateContentConfig(**generation_config)

        # The pinned llama-index Google integration treats generation_config as
        # a pydantic model, not a plain dict. Normalize user/model args too.
        if isinstance(args.get("generation_config"), dict):
            args["generation_config"] = google_types().GenerateContentConfig(**args["generation_config"])

        self.log_llama_create(window, model, args, "PyGPTGoogleGenAI", {"pygpt_remote_tools": built_tools})
        return PyGPTGoogleGenAI(**args, pygpt_remote_tools=built_tools)

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

    def llama_embeddings(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return LlamaIndex embeddings provider

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
        if not args.get("api_key"):
            args["api_key"] = (
                self.get_env_override(
                    window,
                    window.core.config.get("llama.idx.embeddings.env", []) or [],
                    ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
                )
                or self.get_config("api_key", "")
            )
        if args.get("model") and not args.get("model_name"):
            args["model_name"] = args.pop("model")

        window.core.api.google.setup_env()  # setup VertexAI if configured
        args = self.inject_llamaindex_embedding_http_clients(args, window.core.config)
        self.log_llama_create(
            window, None, args, "GoogleGenAIEmbedding",
            kind="embeddings",
        )
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
            http_options = google_types().HttpOptions(
                client_args={"proxy": proxy},
                async_client_args={"proxy": proxy},
            )
            args["http_options"] = http_options
        return args

    def inject_llamaindex_embedding_http_clients(self, args: dict, cfg) -> dict:
        if "http_options" in args:
            return args
        proxy = cfg.get("api_proxy")
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        options = {
            "timeout": int(self.get_embeddings_timeout(cfg) * 1000),
        }
        if proxy:
            options["client_args"] = {"proxy": proxy}
            options["async_client_args"] = {"proxy": proxy}
        args["http_options"] = google_types().HttpOptions(**options)
        return args
