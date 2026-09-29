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

from __future__ import annotations

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
    from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
    MODE_EMBEDDINGS,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class xAILLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(xAILLM, self).__init__(*args, **kwargs)
        self.id = "x_ai"
        self.name = "xAI"
        self.type = [MODE_CHAT, MODE_LLAMA_INDEX, MODE_EMBEDDINGS]

    def setup(self) -> dict:
        return {
            "settings": {
                "api_key": {
                    "type": "str", "default": "", "secret": True,
                    "urls": {"API Keys": "https://console.x.ai"},
                },
                "api_base": {"type": "str", "default": "https://api.x.ai/v1"},
                "extra": {
                    "management_api_key": {
                        "type": "str", "default": "", "secret": True,
                        "label": "settings.api_key_management.xai",
                        "desc": "settings.api_key_management.xai.desc",
                        "use_locale": True,
                        "urls": {"API Keys": "https://console.x.ai"},
                    },
                    "native": {
                        "type": "bool", "default": True,
                        "label": "settings.api_native_xai",
                        "desc": "settings.api_native_xai.desc",
                        "use_locale": True,
                    },
                },
            },
            "remote_tools": {
                "web_search": {
                    "unsupported_prefixes": ['grok-3'],
                    "unsupported_models": [],
                    "type": "bool",
                    "label": "settings.remote_tools.xai.web_search",
                    "default": True,
                    "desc": "settings.remote_tools.xai.web_search.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.web_search",
                    "tool": True,
                },
                "x_search": {
                    "type": "bool",
                    "label": "settings.remote_tools.xai.x_search",
                    "default": False,
                    "desc": "settings.remote_tools.xai.x_search.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.x_search",
                    "tool": True,
                },
                "code_execution": {
                    "type": "bool",
                    "label": "settings.remote_tools.xai.code_execution",
                    "default": False,
                    "desc": "settings.remote_tools.xai.code_execution.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.code_execution",
                    "tool": True,
                },
                "mcp": {
                    "type": "bool",
                    "label": "settings.remote_tools.xai.mcp",
                    "default": False,
                    "desc": "settings.remote_tools.xai.mcp.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.mcp",
                    "tool": True,
                },
                "mcp.args": {
                    "type": "textarea",
                    "label": "settings.remote_tools.xai.mcp.args",
                    "urls": {
                        "xAI Docs": "https://docs.x.ai/docs/guides/tools/remote-mcp-tools",
                    },
                    "default": "{\n    \"server_url\": \"https://mcp.deepwiki.com/mcp\n}",
                    "desc": "settings.remote_tools.xai.mcp.args.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.mcp.args",
                },
                "collections": {
                    "type": "bool",
                    "label": "settings.remote_tools.xai.collections",
                    "default": False,
                    "desc": "settings.remote_tools.xai.collections.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.collections",
                    "tool": True,
                },
                "collections.args": {
                    "type": "text",
                    "label": "settings.remote_tools.xai.collections.args",
                    "urls": {
                        "xAI Docs": "https://docs.x.ai/docs/guides/tools/collections-search-tool",
                    },
                    "default": "",
                    "desc": "settings.remote_tools.xai.collections.args.desc",
                    "use_locale": True,
                    "legacy_key": "remote_tools.xai.collections.args",
                },
                "return_citations": {
                    "type": "bool",
                    "default": True,
                    "label": "Return citations",
                    "desc": "Optional provider tool parameter: return_citations",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.return_citations",
                },
                "max_results": {
                    "type": "int",
                    "default": 0,
                    "label": "Max results",
                    "desc": "Optional provider tool parameter: max_results",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.max_results",
                    "min": 0,
                },
                "inline_citations": {
                    "type": "bool",
                    "default": True,
                    "label": "Inline citations",
                    "desc": "Optional provider tool parameter: inline_citations",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.inline_citations",
                },
                "include_code_output": {
                    "type": "bool",
                    "default": True,
                    "label": "Include code output",
                    "desc": "Optional provider tool parameter: include_code_output",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.include_code_output",
                },
                "use_encrypted_content": {
                    "type": "bool",
                    "default": False,
                    "label": "Use encrypted content",
                    "desc": "Optional provider tool parameter: use_encrypted_content",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.use_encrypted_content",
                },
                "max_turns": {
                    "type": "int",
                    "default": 0,
                    "label": "Max turns",
                    "desc": "Optional provider tool parameter: max_turns",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.max_turns",
                    "min": 0,
                },
                "x.included_handles": {
                    "type": "text",
                    "default": "",
                    "label": "X / included handles",
                    "desc": "Optional provider tool parameter: x.included_handles",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.included_handles",
                },
                "x.excluded_handles": {
                    "type": "text",
                    "default": "",
                    "label": "X / excluded handles",
                    "desc": "Optional provider tool parameter: x.excluded_handles",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.excluded_handles",
                },
                "x.min_favs": {
                    "type": "int",
                    "default": 0,
                    "label": "X / min favs",
                    "desc": "Optional provider tool parameter: x.min_favs",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.min_favs",
                    "min": 0,
                },
                "x.min_views": {
                    "type": "int",
                    "default": 0,
                    "label": "X / min views",
                    "desc": "Optional provider tool parameter: x.min_views",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.min_views",
                    "min": 0,
                },
                "from_date": {
                    "type": "text",
                    "default": "",
                    "label": "From date",
                    "desc": "Optional provider tool parameter: from_date",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.from_date",
                },
                "to_date": {
                    "type": "text",
                    "default": "",
                    "label": "To date",
                    "desc": "Optional provider tool parameter: to_date",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.to_date",
                },
                "web.country": {
                    "type": "text",
                    "default": "",
                    "label": "Web / country",
                    "desc": "Optional provider tool parameter: web.country",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.country",
                },
                "web.safe_search": {
                    "type": "combo",
                    "default": "",
                    "label": "Web / safe search",
                    "desc": "Optional provider tool parameter: web.safe_search",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.safe_search",
                    "choices": [{'': 'Default'}, {'true': 'Enabled'}, {'false': 'Disabled'}],
                    "value_type": "optional_bool",
                },
                "web.enable_image_understanding": {
                    "type": "bool",
                    "default": False,
                    "label": "Web / enable image understanding",
                    "desc": "Optional provider tool parameter: web.enable_image_understanding",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.enable_image_understanding",
                },
                "x.enable_image_understanding": {
                    "type": "bool",
                    "default": False,
                    "label": "X / enable image understanding",
                    "desc": "Optional provider tool parameter: x.enable_image_understanding",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.enable_image_understanding",
                },
                "x.enable_video_understanding": {
                    "type": "bool",
                    "default": False,
                    "label": "X / enable video understanding",
                    "desc": "Optional provider tool parameter: x.enable_video_understanding",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.x.enable_video_understanding",
                },
                "web.allowed_websites": {
                    "type": "text",
                    "default": "",
                    "label": "Web / allowed websites",
                    "desc": "Optional provider tool parameter: web.allowed_websites",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.allowed_websites",
                },
                "web.excluded_websites": {
                    "type": "text",
                    "default": "",
                    "label": "Web / excluded websites",
                    "desc": "Optional provider tool parameter: web.excluded_websites",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.excluded_websites",
                },
                "web.enable_image_search": {
                    "type": "bool",
                    "default": False,
                    "label": "Web / enable image search",
                    "desc": "Optional provider tool parameter: web.enable_image_search",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.web.enable_image_search",
                },
                "store_messages": {
                    "type": "combo",
                    "default": "",
                    "label": "Store messages",
                    "desc": "Optional provider tool parameter: store_messages",
                    "advanced": True,
                    "use_locale": False,
                    "legacy_key": "remote_tools.xai.store_messages",
                    "choices": [{'': 'Default'}, {'true': 'Enabled'}, {'false': 'Disabled'}],
                    "value_type": "optional_bool",
                },
                "mode": {
                    "type": "text",
                    "default": "auto",
                    "hidden": True,
                    "legacy_key": "remote_tools.xai.mode",
                },
                "sources.news": {
                    "type": "text",
                    "default": False,
                    "hidden": True,
                    "legacy_key": "remote_tools.xai.sources.news",
                },
                "sources.web": {
                    "type": "text",
                    "default": True,
                    "hidden": True,
                    "legacy_key": "remote_tools.xai.sources.web",
                },
                "sources.x": {
                    "type": "text",
                    "default": True,
                    "hidden": True,
                    "legacy_key": "remote_tools.xai.sources.x",
                },
            },
        }

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

        args = self.prepare_openai_compatible_args(window, model)
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

    def _llama_responses(
            self,
            window,
            model: ModelItem,
            remote_cfg: Dict,
    ) -> LlamaBaseLLM:
        """Build an xAI Responses/Agent Tools LlamaIndex adapter."""
        from .responses_agent import AgentXAIResponses

        args = self.prepare_openai_compatible_args(window, model)

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

        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning"] = {"effort": reasoning_effort}
            args["additional_kwargs"] = additional_kwargs

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

        self.log_llama_create(window, model, args, "AgentXAIResponses")
        return AgentXAIResponses(**args)

    def llama_agent(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True,
            force_computer_use: bool = False,
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
        from .llama_index.embedding import XAIEmbedding as BaseXAIEmbedding

        cfg = window.core.config

        args = self.prepare_openai_compatible_embedding_args(window, config)

        proxy = cfg.get("api_proxy") or self.get_config("proxy")
        if not cfg.get("api_proxy.enabled", False):
            proxy = ""
        timeout = self.get_embeddings_timeout(cfg)

        # 1) REST (OpenAI-compatible)
        try_args = dict(args)
        try:
            try_args = self.inject_llamaindex_embedding_http_clients(try_args, cfg)
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
