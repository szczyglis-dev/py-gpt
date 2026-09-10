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
        Return xAI LLM for the regular LlamaIndex / Chat with files path.

        xAI deprecated Live Search ``search_parameters`` on Chat Completions.
        When provider-native remote tools are enabled, use the
        OpenAI-compatible Responses API and xAI Agent Tools instead.

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :param remote_tools: allow provider-native remote tools
        :return: LLM provider instance
        """
        if remote_tools:
            try:
                remote_cfg = window.core.api.xai.remote.build_for_responses(model=model) or {}
            except Exception as e:
                window.core.debug.log(e)
                remote_cfg = {}

            if remote_cfg.get("tools"):
                return self._llama_responses(
                    window=window,
                    model=model,
                    remote_cfg=remote_cfg,
                )

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
        return OpenAILike(**args)

    def _llama_responses(
            self,
            window,
            model: ModelItem,
            remote_cfg: Dict,
    ) -> LlamaBaseLLM:
        """Build an xAI Responses/Agent Tools LlamaIndex adapter."""
        from pygpt_net.provider.llms.x_ai_responses_agent import AgentXAIResponses

        args = self.parse_args(model.llama_index, window)
        args["model"] = args.get("model") or model.id
        args["api_key"] = args.get("api_key") or window.core.config.get("api_key_xai", "")
        args["api_base"] = args.get("api_base") or window.core.config.get(
            "api_endpoint_xai",
            "https://api.x.ai/v1",
        )

        # Grok 3 does not support the current server-side Agent Tools. Mirror
        # normal xAI Chat and Agents v2 by switching to the configured fallback.
        if str(args["model"] or "").lower().startswith("grok-3"):
            args["model"] = window.core.config.get("xai_tools_fallback_model") or "grok-4.5-latest"

        # OpenAILike/Chat Completions and OpenAIResponses use different names
        # for the output-token limit and different capability-only arguments.
        if "max_tokens" in args and "max_output_tokens" not in args:
            args["max_output_tokens"] = args.pop("max_tokens")
        args.pop("is_chat_model", None)
        args.pop("is_function_calling_model", None)
        args = self.inject_llamaindex_http_clients(args, window.core.config)

        args["built_in_tools"] = list(remote_cfg.get("tools") or [])
        include = list(remote_cfg.get("include") or [])
        if include:
            current = args.get("include")
            if isinstance(current, list):
                include = [*current, *include]
            elif current:
                include = [current, *include]
            args["include"] = list(dict.fromkeys(include))

        ctx_size = int(getattr(model, "ctx", 0) or 0)
        if ctx_size > 0 and "context_window" not in args:
            args["context_window"] = ctx_size

        return AgentXAIResponses(**args)

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True
    ) -> LlamaBaseLLM:
        """Return xAI LLM for Agents v2.

        xAI removed Live Search ``search_parameters`` from Chat Completions.
        When provider-native Agent Tools are enabled, use xAI's
        OpenAI-compatible Responses API instead. Local FunctionAgent tools are
        merged by LlamaIndex with the server-side xAI tool descriptors.
        """
        if not allow_remote_tools:
            return self.llama(
                window=window,
                model=model,
                stream=stream,
                remote_tools=False,
            )

        try:
            remote_cfg = window.core.api.xai.remote.build_for_responses(model=model) or {}
        except Exception as e:
            window.core.debug.log(e)
            remote_cfg = {}

        built_tools = remote_cfg.get("tools") or []
        if not built_tools:
            return self.llama(
                window=window,
                model=model,
                stream=stream,
                remote_tools=False,
            )

        return self._llama_responses(
            window=window,
            model=model,
            remote_cfg=remote_cfg,
        )

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
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
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
