#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.19 19:00:00                  #
# ================================================== #

import os.path
import chromadb

from llama_index.indices.base import BaseIndex
from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
)
from llama_index.vector_stores import ChromaVectorStore

from .base import BaseStore


class ChromaProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(ChromaProvider, self).__init__(*args, **kwargs)
        """
        Chroma vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "ChromaVectorStore"
        self.prefix = "chroma_"  # prefix for index directory
        self.indexes = {}

    def get_db(self, id: str):
        """
        Get database instance

        :param id: index name
        :return: database instance
        """
        path = self.get_path(id)
        return chromadb.PersistentClient(
            path=path,
        )

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            index = VectorStoreIndex([])  # create empty index
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
        db = self.get_db(id)
        chroma_collection = db.get_or_create_collection(id)
        vector_store = ChromaVectorStore(
            chroma_collection=chroma_collection,
        )
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
        )
        self.indexes[id] = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
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
