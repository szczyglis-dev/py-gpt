#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.13 01:00:00                  #
# ================================================== #

import os.path

from llama_index.core.llms.llm import BaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.indices.service_context import ServiceContext
from llama_index.llms.openai import OpenAI

from pygpt_net.item.model import ModelItem


class Llm:
    def __init__(self, window=None):
        """
        LLMs core

        :param window: Window instance
        """
        self.window = window

    def init(self):
        """Init env vars"""
        os.environ['OPENAI_API_KEY'] = str(self.window.core.config.get('api_key'))
        os.environ['OPENAI_ORGANIZATION'] = str(self.window.core.config.get('organization_key'))

    def get(self, model: ModelItem = None) -> BaseLLM:
        """
        Get LLM provider

        :param model: Model item
        :return: Llama LLM instance
        """
        llm = None
        if model is not None:
            if 'provider' in model.llama_index:
                provider = model.llama_index['provider']
                if provider in self.window.core.llm.llms:
                    try:
                        # init env vars
                        self.window.core.llm.llms[provider].init(
                            window=self.window,
                            model=model,
                            mode="llama_index",
                            sub_mode="",
                        )
                        # get llama LLM instance
                        llm = self.window.core.llm.llms[provider].llama(
                            window=self.window,
                            model=model,
                        )
                    except Exception as e:
                        print(e)

        # default
        if llm is None:
            self.init()  # init env vars
            llm = OpenAI(
                temperature=0.0,
                model="gpt-3.5-turbo",
            )
        return llm

    def get_embeddings_provider(self) -> BaseEmbedding:
        """
        Get embeddings provider

        :return: Llama embeddings provider instance
        """
        provider = self.window.core.config.get("llama.idx.embeddings.provider", "openai")
        self.window.core.llm.llms[provider].init_embeddings(
            window=self.window,
        )
        return self.window.core.llm.llms[provider].get_embeddings_model(
            window=self.window,
        )

    def get_service_context(self, model: ModelItem = None) -> ServiceContext:
        """
        Get service context + embeddings provider

        :param model: Model item
        :return: Service context instance
        """
        llm = self.get(model=model)
        embed_model = self.get_embeddings_provider()

        kwargs = {}
        if llm is not None:
            kwargs['llm'] = llm
        if embed_model is not None:
            kwargs['embed_model'] = embed_model

        return ServiceContext.from_defaults(**kwargs)
