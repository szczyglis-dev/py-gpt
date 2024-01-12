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


class Storage:
    def __init__(self, window=None):
        """
        Index storage core

        :param window: Window instance
        """
        self.window = window
        self.indexes = {}

    def get_service_context(self, model: str = "gpt-3.5-turbo"):
        """
        Get service context

        :param model: Model name
        :return: Service context
        """
        # GPT
        if model.startswith("gpt-") or model.startswith("text-davinci-"):
            os.environ['OPENAI_API_KEY'] = self.window.core.config.get("api_key")
            llm = OpenAI(temperature=0.0, model=model)
            return ServiceContext.from_defaults(llm=llm)
        # TODO: add other models

    def exists(self, id: str):
        """
        Check if index exists

        :param id: Index name
        :return: True if exists
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        return os.path.exists(path)

    def create(self, id: str, model: str = "gpt-3.5-turbo"):
        """
        Create empty index

        :param id: Index name
        :param model: Model name
        """
        # ctx create is required to set environment variables here:
        self.get_service_context(model=model)

        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        if not os.path.exists(path):
            index = VectorStoreIndex([])  # create empty index
            self.store(id=id, index=index)

    def get(self, id: str, model: str = "gpt-3.5-turbo"):
        """
        Get index

        :param id: Index name
        :param model: Model name
        :return: Index
        """
        if not self.exists(id=id):
            self.create(id=id, model=model)

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
