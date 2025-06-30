#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 20:00:00                  #
# ================================================== #

import os.path
from typing import Optional, Union

from llama_index.core.llms.llm import BaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.llms.openai import OpenAI

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from pygpt_net.item.model import ModelItem


class Llm:
    def __init__(self, window=None):
        """
        LLM provider core

        :param window: Window instance
        """
        self.window = window
        self.default_model = "gpt-4o-mini"
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
            stream: bool = False
    ) -> Union[BaseLLM, MultiModalLLM]:
        """
        Get LLM provider

        :param model: Model item
        :param multimodal: Allow multi-modal flag (True to get multimodal provider if available)
        :param stream: Stream mode (True to enable streaming)
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
            if provider in self.window.core.llm.llms:
                # init env vars
                self.window.core.llm.llms[provider].init(
                    window=self.window,
                    model=model,
                    mode=MODE_LLAMA_INDEX,
                    sub_mode="",
                )
                # get llama LLM instance
                if multimodal and model.is_multimodal():
                    # at first, try to get multimodal provider
                    llm = self.window.core.llm.llms[provider].llama_multimodal(
                        window=self.window,
                        model=model,
                    )
                    if llm is not None:
                        print("Using multimodal.")

                if llm is None:
                    # if no multimodal, get default llama provider
                    llm = self.window.core.llm.llms[provider].llama(
                        window=self.window,
                        model=model,
                        stream=stream,
                    )

        # default model
        if llm is None:
            self.init()  # init env vars
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

        if provider is None or provider not in self.window.core.llm.llms:
            provider = self.default_embed

        self.window.core.llm.llms[provider].init_embeddings(
            window=self.window,
            env=env,
        )
        return self.window.core.llm.llms[provider].get_embeddings_model(
            window=self.window,
            config=args,
        )

    def get_service_context(
            self,
            model: Optional[ModelItem] = None,
            stream: bool = False,
    ):
        """
        Get service context + embeddings provider

        :param model: Model item (for query)
        :param stream: Stream mode (True to enable streaming)
        :return: Service context instance
        """
        llm = self.get(model=model, stream=stream)
        embed_model = self.get_embeddings_provider()
        return llm, embed_model
