#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 18:00:00                  #
# ================================================== #

import os.path
from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
    load_index_from_storage,
)

from .base import BaseStore


class SimpleProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(SimpleProvider, self).__init__(*args, **kwargs)
        """
        Simple vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "SimpleVectorStore"
        self.indexes = {}

    def exists(self, id: str = None) -> bool:
        """
        Check if index with id exists

        :param id: index name
        :return: True if exists
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        return os.path.exists(path)

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        if not os.path.exists(path):
            index = VectorStoreIndex([])  # create empty index
            self.store(id=id, index=index)

    def get(self, id: str, service_context: ServiceContext = None) -> VectorStoreIndex:
        """
        Get index

        :param id: index name
        :param service_context: Service context
        :return: index instance
        """
        if not self.exists(id=id):
            self.create(id=id)
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        storage_context = StorageContext.from_defaults(persist_dir=path)
        self.indexes[id] = load_index_from_storage(storage_context, service_context=service_context)
        return self.indexes[id]

    def store(self, id: str, index: VectorStoreIndex = None):
        """
        Store index

        :param id: index name
        :param index: index instance
        """
        if index is None:
            index = self.indexes[id]
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        index.storage_context.persist(persist_dir=path)
        self.indexes[id] = index

    def remove(self, id: str) -> bool:
        """
        Truncate index

        :param id: index name
        :return: True if success
        """
        self.indexes[id] = None
        path = os.path.join(self.window.core.config.get_user_dir('idx'), id)
        if os.path.exists(path):
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
            os.rmdir(path)
        return True
