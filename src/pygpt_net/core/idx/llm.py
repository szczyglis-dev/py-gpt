#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.20 18:00:00                  #
# ================================================== #

import os.path
from llama_index import (
    ServiceContext,
)
from llama_index.llms import OpenAI

from pygpt_net.item.model import ModelItem


class Llm:
    def __init__(self, window=None):
        """
        Index LLM core

        :param window: Window instance
        """
        self.window = window
        self.indexes = {}

    def init(self):
        """Init env vars"""
        os.environ['OPENAI_API_KEY'] = self.window.core.config.get('api_key')

    def get(self, model: ModelItem = None):
        """
        Get LLM provider

        :param model: Model item
        :return: LLM
        """
        llm = None
        if model is not None:
            if 'provider' in model.llama_index:
                provider = model.llama_index['provider']
                if provider in self.window.core.llm.llms:
                    try:
                        # init
                        self.window.core.llm.llms[provider].init(
                            self.window, model, "llama_index", "")
                        # get llama llm instance
                        llm = self.window.core.llm.llms[provider].llama(
                            self.window, model)
                    except Exception as e:
                        print(e)

        # default
        if llm is None:
            os.environ['OPENAI_API_KEY'] = self.window.core.config.get('api_key')
            llm = OpenAI(temperature=0.0, model="gpt-3.5-turbo")
        return llm

    def get_service_context(self, model: ModelItem = None):
        """
        Get service context

        :param model: Model item
        :return: Service context
        """
        llm = self.get(model=model)
        if llm is None:
            return ServiceContext.from_defaults()
        return ServiceContext.from_defaults(llm=llm)
