#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 20:00:00                  #
# ================================================== #

from typing import Optional, List, Dict

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class xAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(xAILLM, self).__init__(*args, **kwargs)
        self.id = "x_ai"
        self.name = "xAI"
        self.type = [MODE_CHAT, MODE_LLAMA_INDEX, "embeddings"]

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
        from llama_index.llms.openai_like import OpenAILike
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = window.core.config.get("api_key_xai", "")
        if "api_base" not in args or args["api_base"] == "":
            args["api_base"] = window.core.config.get("api_endpoint_xai", "https://api.x.ai/v1")
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        args = self.inject_llamaindex_http_clients(args, window.core.config)

        # -----------------------------------------------------------
        # xAI Live Search via search_parameters (Chat Completions)
        # LlamaIndex OpenAILike supports 'additional_kwargs' passed to request body.
        # -----------------------------------------------------------
        try:
            xai_remote = window.core.api.xai.remote.build(model=model) or {}
        except Exception as e:
            window.core.debug.log(e)
            xai_remote = {}

        search_http = xai_remote.get("http")
        if search_http:
            add_kwargs = dict(args.get("additional_kwargs") or {})
            extra_body = dict(add_kwargs.get("extra_body") or {})
            # Do not overwrite if user already set search_parameters manually
            extra_body.setdefault("search_parameters", search_http)
            add_kwargs["extra_body"] = extra_body
            args["additional_kwargs"] = add_kwargs

        return OpenAILike(**args)

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
        pass

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        """
        Return provider instance for embeddings (xAI)

        :param window: window instance
        :param config: config keyword arguments list
        :return: Embedding provider instance
        """
        from .llama_index.x_ai.embedding import XAIEmbedding as BaseXAIEmbedding

        cfg = window.core.config

        args: Dict = {}
        if config is not None:
            args = self.parse_args({"args": config}, window)

        if "api_key" not in args or not args["api_key"]:
            args["api_key"] = cfg.get("api_key_xai", "")

        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        # if OpenAI-compatible
        if "api_base" not in args or not args["api_base"]:
            args["api_base"] = cfg.get("api_endpoint_xai", "https://api.x.ai/v1")

        proxy = cfg.get("api_proxy") or cfg.get("api_native_xai.proxy")
        timeout = cfg.get("api_native_xai.timeout")

        # 1) REST (OpenAI-compatible)
        try_args = dict(args)
        try:
            try_args = self.inject_llamaindex_http_clients(try_args, cfg)
            return BaseXAIEmbedding(**try_args)
        except TypeError:
            # goto gRPC
            pass

        # 2) Fallback: gRPC (xai_sdk)
        def _build_xai_grpc_client(api_key: str, proxy_url: Optional[str], timeout_val: Optional[float]):
            import os
            import xai_sdk
            kwargs = {"api_key": api_key}
            if timeout_val is not None:
                kwargs["timeout"] = timeout_val

            # channel_options - 'grpc.http_proxy'
            if proxy_url:
                try:
                    kwargs["channel_options"] = [("grpc.http_proxy", proxy_url)]
                except TypeError:
                    # ENV
                    os.environ["grpc_proxy"] = proxy_url

            try:
                return xai_sdk.Client(**kwargs)
            except TypeError:
                if proxy_url:
                    os.environ["grpc_proxy"] = proxy_url
                return xai_sdk.Client(api_key=api_key)

        xai_client = _build_xai_grpc_client(args.get("api_key", ""), proxy, timeout)

        # gRPC
        class XAIEmbeddingWithProxy(BaseXAIEmbedding):
            def __init__(self, *a, injected_client=None, **kw):
                super().__init__(*a, **kw)
                if injected_client is not None:
                    for attr in ("client", "_client", "_xai_client"):
                        if hasattr(self, attr):
                            setattr(self, attr, injected_client)
                            break

        return XAIEmbeddingWithProxy(**args, injected_client=xai_client)

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
