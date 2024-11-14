#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 05:00:00                  #
# ================================================== #

import os.path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.service_context import ServiceContext

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
        self.prefix = ""  # prefix for index directory
        self.indexes = {}

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            index = self.index_from_empty()  # create empty index
            self.store(
                id=id,
                index=index,
            )

    def get(self, id: str, service_context: ServiceContext = None) -> BaseIndex:
        """
        Get index

        :param id: index name
        :param service_context: Service context
        :return: index instance
        """
        if not self.exists(id):
            self.create(id)
        path = self.get_path(id)
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
        )
        self.indexes[id] = load_index_from_storage(
            storage_context,
            service_context=service_context,
        )
        return self.indexes[id]

    def store(self, id: str, index: BaseIndex = None):
        """
        Store index

        :param id: index name
        :param index: index instance
        """
        if index is None:
            index = self.indexes[id]
        path = self.get_path(id)
        index.storage_context.persist(
            persist_dir=path,
        )
        self.indexes[id] = index
