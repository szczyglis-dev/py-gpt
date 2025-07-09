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

import os
from typing import Optional, List, Dict

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM

from pygpt_net.core.types import (
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
)
from pygpt_net.item.model import ModelItem
from pygpt_net.utils import parse_args


class BaseLLM:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.name = ""
        self.type = []  # langchain, llama_index, embeddings
        self.description = ""

    def init(
            self,
            window,
            model: ModelItem,
            mode: str,
            sub_mode: str = None
    ):
        """
        Initialize provider

        :param window: window instance
        :param model: model instance
        :param mode: mode (langchain, llama_index)
        :param sub_mode: sub mode (chat, completion)
        """
        options = {}
        if mode == MODE_LANGCHAIN:
            pass
            # options = model.langchain
        elif mode == MODE_LLAMA_INDEX:
            options = model.llama_index
        if 'env' in options:
            for item in options['env']:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

    def init_embeddings(
            self,
            window,
            env: Optional[List[Dict]] = None
    ):
        """
        Initialize embeddings provider

        :param window: window instance
        :param env: ENV configuration list
        """
        if env is not None and len(env) > 0:
            for item in env:
                if item['name'] is None or item['name'] == "":
                    continue
                try:
                    os.environ[item['name']] = str(item['value'].format(**window.core.config.all()))
                except Exception as e:
                    pass

    def parse_args(
            self,
            options: dict,
            window = None
    ) -> dict:
        """
        Parse extra args

        :param options: LLM options dict (langchain, llama_index)
        :param window: window instance
        :return: parsed arguments dict
        """
        args = {}
        if 'args' in options:
            if options['args'] is not None:
                args = parse_args(options['args'])
                if window:
                    for key in args:
                        if isinstance(args[key], str):
                            try:
                                args[key] = args[key].format(**window.core.config.all())
                            except Exception as e:
                                pass
        return args

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for completion in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> any:
        """
        Return LLM provider instance for chat in langchain mode

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama index query and chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: provider instance
        """
        pass

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
        :return: provider instance
        """
        pass
