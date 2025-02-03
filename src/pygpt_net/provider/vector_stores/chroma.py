#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 01:00:00                  #
# ================================================== #

import os.path
from typing import Optional

import chromadb
from chromadb.config import Settings

from llama_index.core.indices.base import BaseIndex
from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

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
            settings=Settings(
                anonymized_telemetry=False
            )
        )

    def create(
            self,
            id: str,
            embed_model: Optional = None):
        """
        Create empty index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            index = self.index_from_empty(embed_model)  # create empty index
            self.store(
                id=id,
                index=index,
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
            self.create(id, embed_model)
        path = self.get_path(id)
        db = self.get_db(id)
        chroma_collection = db.get_or_create_collection(id)
        vector_store = ChromaVectorStore(
            chroma_collection=chroma_collection,
        )
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
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
        if index is None:
            index = self.indexes[id]
        path = self.get_path(id)
        index.storage_context.persist(
            persist_dir=path,
        )
        self.indexes[id] = index
