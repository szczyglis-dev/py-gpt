#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:18:00                  #
# ================================================== #

from typing import Optional, List, Dict

# from langchain_openai import OpenAI
# from langchain_openai import ChatOpenAI

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    MODE_CHAT,
    MODE_AGENT_V2,
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

    def llama_completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """Return an OpenAI LlamaIndex adapter for PyGPT Completion mode.

        LlamaIndex exposes ``complete`` / ``stream_complete`` for both legacy
        completion models and chat models. ``OpenAILike`` is used deliberately
        here so newly released OpenAI model IDs do not depend on LlamaIndex's
        hard-coded OpenAI model registry.
        """
        from llama_index.llms.openai_like import OpenAILike

        class OpenAICompletion(OpenAILike):
            """Normalize Chat Completions kwargs for OpenAI reasoning models."""

            @staticmethod
            def _is_reasoning_model(model_id: str) -> bool:
                model_id = str(model_id or "").lower()
                return model_id.startswith(("o1", "o3", "o4", "gpt-5", "gpt-6"))

            def _get_model_kwargs(self, **kwargs):
                params = super()._get_model_kwargs(**kwargs)
                if not self._is_reasoning_model(self.model):
                    return params

                # Reasoning models do not share the classic sampling surface.
                # Keep Completion mode compatible with current Chat Completions
                # models and avoid parameters rejected by newer GPT/o-series IDs.
                for key in (
                        "temperature",
                        "top_p",
                        "presence_penalty",
                        "frequency_penalty",
                        "stop",
                ):
                    params.pop(key, None)

                if "max_tokens" in params:
                    params.setdefault("max_completion_tokens", params["max_tokens"])
                    params.pop("max_tokens", None)
                return params

        args = self.parse_args(model.llama_index, window)
        model_id = str(args.get("model") or model.id or "").strip()
        if model_id.startswith("text-davinci"):
            # Preserve PyGPT's historical compatibility fallback.
            model_id = "gpt-3.5-turbo-instruct"
        if not model_id:
            raise ValueError("Model name is required for OpenAI completion.")
        args["model"] = model_id

        # Use the same credentials/endpoints as the native OpenAI client,
        # including per-model API overrides. OpenAILike expects api_base.
        custom_api_key = (getattr(model, "custom_api_key", "") or "").strip()
        custom_api_endpoint = (getattr(model, "custom_api_endpoint", "") or "").strip()
        if not args.get("api_key"):
            args["api_key"] = custom_api_key or window.core.config.get("api_key", "")
        if not args.get("api_base"):
            api_base = custom_api_endpoint or window.core.config.get("api_endpoint", "")
            if api_base:
                args["api_base"] = api_base

        organization = str(window.core.config.get("organization_key", "") or "").strip()
        if organization:
            headers = dict(args.get("default_headers") or {})
            headers.setdefault("OpenAI-Organization", organization)
            args["default_headers"] = headers

        if "context_window" not in args:
            ctx_size = int(getattr(model, "ctx", 0) or 0)
            if ctx_size > 0:
                args["context_window"] = ctx_size

        # A model configured for Chat in PyGPT uses /v1/chat/completions even
        # though the UI mode is Completion. Legacy instruct-only models stay on
        # /v1/completions. This also bypasses LlamaIndex model-name detection.
        args.setdefault("is_chat_model", model.has_mode(MODE_CHAT))
        args.setdefault("is_function_calling_model", False)

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAICompletion(**args)

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
        from llama_index.llms.openai import OpenAI as LlamaOpenAI
        from llama_index.llms.openai import OpenAIResponses as LlamaOpenAIResponses
        args = self.parse_args(model.llama_index, window)
        if "api_key" not in args:
            args["api_key"] = window.core.config.get("api_key", "")
        if "model" not in args:
            args["model"] = model.id

        args = self.inject_llamaindex_http_clients(args, window.core.config)
        mode = window.core.config.get("mode")
        # dont' use Responses in agent modes
        if window.core.config.get('api_use_responses_llama', False) and mode == MODE_LLAMA_INDEX:
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

    def llama_chat_with_files(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            computer_runtime=None,
    ) -> LlamaBaseLLM:
        """Use the shared provider continuation adapter when Computer Use is active."""
        tools = window.core.api.openai.remote_tools.append_to_tools(
            mode=MODE_LLAMA_INDEX,
            model=model,
            stream=stream,
            is_expert_call=False,
            tools=[],
            preset=None,
        )
        if any(isinstance(tool, dict) and tool.get("type") == "computer" for tool in tools):
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
        """
        Return OpenAI LLM for Agents v2.

        Provider-native remote tools are attached directly to OpenAI Responses,
        exactly through the same PyGPT remote-tools builder used by normal Chat.
        Local FunctionAgent tools are merged by LlamaIndex at request time.
        """
        from llama_index.llms.openai import OpenAI as LlamaOpenAI
        from pygpt_net.provider.llms.openai_responses_agent import AgentOpenAIResponses

        args = self.parse_args(model.llama_index, window)
        if "api_key" not in args:
            args["api_key"] = window.core.config.get("api_key", "")
        if "model" not in args:
            args["model"] = model.id
        args = self.inject_llamaindex_http_clients(args, window.core.config)

        if allow_remote_tools:
            tools = window.core.api.openai.remote_tools.append_to_tools(
                mode=MODE_AGENT_V2,
                model=model,
                stream=stream,
                is_expert_call=False,
                tools=[],
                preset=None,
            )
            if tools:
                args["built_in_tools"] = tools

                # Keep the same complete hosted-web-search sources payload that
                # normal PyGPT Chat requests from the Responses API.
                web_types = {
                    "web_search",
                    "web_search_preview",
                    "web_search_2025_08_26",
                    "web_search_preview_2025_03_11",
                }
                if any(
                        isinstance(tool, dict) and tool.get("type") in web_types
                        for tool in tools
                ):
                    include_value = args.get("include")
                    if isinstance(include_value, list):
                        include = list(include_value)
                    elif include_value:
                        include = [include_value]
                    else:
                        include = []
                    source_field = "web_search_call.action.sources"
                    if source_field not in include:
                        include.append(source_field)
                    args["include"] = include

                return AgentOpenAIResponses(**args)

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
        pass

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