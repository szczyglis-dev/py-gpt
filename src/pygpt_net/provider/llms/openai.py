#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.09 22:00:00                  #
# ================================================== #

from typing import Optional, List, Dict

# from langchain_openai import OpenAI
# from langchain_openai import ChatOpenAI

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.llms.openai import OpenAIResponses as LlamaOpenAIResponses
from llama_index.multi_modal_llms.openai import OpenAIMultiModal as LlamaOpenAIMultiModal
from llama_index.embeddings.openai import OpenAIEmbedding

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
    OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER,
    OPENAI_REMOTE_TOOL_DISABLE_IMAGE,
    OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH,
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
        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id

        if window.core.config.get('api_use_responses_llama', False):
            tools = []
            if (not model.id.startswith("o1")
                    and not model.id.startswith("o3")):

                if not model.id in OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH:
                    if window.core.config.get("remote_tools.web_search", False):
                        tools.append({"type": "web_search_preview"})

                if not model.id in OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER:
                    if window.core.config.get("remote_tools.code_interpreter", False):
                        tools.append({
                            "type": "code_interpreter",
                            "container": {
                                "type": "auto"
                            }
                        })

                if not model.id in OPENAI_REMOTE_TOOL_DISABLE_IMAGE:
                    if window.core.config.get("remote_tools.image", False):
                        tool = {"type": "image_generation"}
                        if stream:
                            tool["partial_images"] = 1  # required for streaming
                        tools.append(tool)
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
        args = {}
        if config is not None:
            args = self.parse_args({
                "args": config,
            }, window)
        return OpenAIEmbedding(**args)
