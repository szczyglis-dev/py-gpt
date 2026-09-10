#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 12:00:00                  #
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