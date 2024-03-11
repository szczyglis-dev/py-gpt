#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.11 01:00:00                  #
# ================================================== #

import datetime
import os.path

from llama_index.core import StorageContext
from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.service_context import ServiceContext
from llama_index.vector_stores.redis import RedisVectorStore

from pygpt_net.utils import parse_args
from .base import BaseStore


class RedisProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(RedisProvider, self).__init__(*args, **kwargs)
        """
        Redis vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "RedisVectorStore"
        self.prefix = "redis_"  # prefix for index directory
        self.indexes = {}

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            os.makedirs(path)
            self.store(id)

    def get_store(self, id: str) -> RedisVectorStore:
        """
        Get Redis vector store

        :param id: index name
        :return: RedisVectorStore instance
        """
        defaults = {
            "index_name": id,
        }
        additional_args = parse_args(
            self.window.core.config.get('llama.idx.storage.args', []),
        )
        if "index_name" in additional_args:
            del defaults["index_name"]

        return RedisVectorStore(
            **defaults,
            **additional_args
        )

    def get(self, id: str, service_context: ServiceContext = None) -> BaseIndex:
        """
        Get index

        :param id: index name
        :param service_context: service context
        :return: index instance
        """
        if not self.exists(id):
            self.create(id)
        vector_store = self.get_store(id)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
        )
        self.indexes[id] = self.index_from_store(vector_store, storage_context)
        return self.indexes[id]

    def store(self, id: str, index: BaseIndex = None):
        """
        Store index

        :param id: index name
        :param index: index instance
        """
        path = self.get_path(id)
        lock_file = os.path.join(path, 'store.lock')
        with open(lock_file, 'w') as f:
            f.write(id + ': ' + str(datetime.datetime.now()))
        self.get_store(id=id).persist(
            persist_path="",
        )
        self.indexes[id] = index
