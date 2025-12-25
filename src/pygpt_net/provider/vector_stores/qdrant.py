#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.30 13:00:00                  #
# ================================================== #

import datetime
import os.path
from typing import Optional

from llama_index.core.indices.base import BaseIndex
from llama_index.core import StorageContext

from pygpt_net.utils import parse_args
from .base import BaseStore


class QdrantProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(QdrantProvider, self).__init__(*args, **kwargs)
        """
        Qdrant vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "QdrantVectorStore"
        self.prefix = "qdrant_"  # prefix for index directory
        self.indexes = {}

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            self.store(id)

    def get_qdrant_store(self, id: str):
        """
        Get Qdrant vector store

        :param id: index name
        :return: QdrantVectorStore instance
        """
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        
        additional_args = parse_args(
            self.window.core.config.get('llama.idx.storage.args', []),
        )
        
        url = additional_args.get('url', 'http://localhost:6333')
        api_key = additional_args.get('api_key', '')
        
        store_args = {k: v for k, v in additional_args.items() if k not in ['url', 'api_key', 'collection_name']}
        
        return QdrantVectorStore(
            url=url,
            api_key=api_key,
            collection_name=id,
            **store_args
        )

    def get(
            self,
            id: str,
            llm: Optional = None,
            embed_model: Optional = None,
    ) -> BaseIndex:
        """
        Get index

        :param id: index name
        :param llm: LLM instance
        :param embed_model: Embedding model instance
        :return: index instance
        """
        if not self.exists(id):
            self.create(id)
        vector_store = self.get_qdrant_store(id)
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store,
        )
        self.indexes[id] = self.index_from_store(
            vector_store=vector_store,
            storage_context=storage_context,
            llm=llm,
            embed_model=embed_model,
        )
        return self.indexes[id]

    def store(
            self,
            id: str,
            index: Optional[BaseIndex] = None
    ):
        """
        Store index

        :param id: index name
        :param index: index instance
        """
        path = self.get_path(id)
        os.makedirs(path, exist_ok=True)
        lock_file = os.path.join(path, 'store.lock')
        with open(lock_file, 'w') as f:
            f.write(id + ': ' + str(datetime.datetime.now()))
        self.indexes[id] = index
