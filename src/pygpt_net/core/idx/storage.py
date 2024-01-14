#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 10:00:00                  #
# ================================================== #

import os.path
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms import OpenAI

from pygpt_net.item.model import ModelItem


class Storage:
    def __init__(self, window=None):
        """
        Index storage core

        :param window: Window instance
        """
        self.window = window
        self.indexes = {}

    def get_llm(self, model: ModelItem = None):
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

        # create default if model not provided
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
        llm = self.get_llm(model=model)
        if llm is None:
            return ServiceContext.from_defaults()
        return ServiceContext.from_defaults(llm=llm)

    def exists(self, id: str = None):
        """
        Check if index exists

        :param id: Index name
        :return: True if exists
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        return os.path.exists(path)

    def create(self, id: str, model: str = None):
        """
        Create empty index

        :param id: Index name
        :param model: Model key
        """
        self.get_service_context()  # set env vars if needed
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        if not os.path.exists(path):
            index = VectorStoreIndex([])  # create empty index
            self.store(id=id, index=index)

    def get(self, id: str, model: ModelItem = None):
        """
        Get index

        :param id: Index name
        :param model: Model item
        :return: Index
        """
        if not self.exists(id=id):
            self.create(id=id)
        service_context = self.get_service_context(model=model)
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        storage_context = StorageContext.from_defaults(persist_dir=path)
        self.indexes[id] = load_index_from_storage(storage_context, service_context=service_context)
        return self.indexes[id]

    def store(self, id: str, index=None):
        """
        Store index

        :param id: Index name
        :param index: Index
        """
        if index is None:
            index = self.indexes[id]
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        index.storage_context.persist(persist_dir=path)
        self.indexes[id] = index

    def remove(self, id: str) -> bool:
        """
        Truncate index

        :param id: Index name
        :return: True if success
        """
        self.indexes[id] = None
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        if os.path.exists(path):
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
            os.rmdir(path)
        return True
