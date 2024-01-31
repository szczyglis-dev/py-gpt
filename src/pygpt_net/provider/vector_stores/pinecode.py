#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.31 18:00:00                  #
# ================================================== #

import datetime
import os.path

from pinecone import Pinecone, ServerlessSpec

from llama_index.indices.base import BaseIndex
from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
)
from llama_index.vector_stores import PineconeVectorStore

from pygpt_net.utils import parse_args
from .base import BaseStore


class PinecodeProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(PinecodeProvider, self).__init__(*args, **kwargs)
        """
        Pinecone vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "PineconeVectorStore"
        self.indexes = {}

    def get_path(self, id: str) -> str:
        """
        Get database placeholder path

        :param id: index name
        :return: database path
        """
        return os.path.join(
            self.window.core.config.get_user_dir('idx'),
            'pinecode_' + id,
        )

    def exists(self, id: str = None) -> bool:
        """
        Check if index with id exists

        :param id: index name
        :return: True if exists
        """
        path = self.get_path(id)
        return os.path.exists(path)

    def create_index(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        # spec kwargs
        spec_kwargs = {
            "cloud": "aws",
            "region": "us-west-2",
        }
        allowed_additional = ["cloud", "region"]
        kwargs_additional = parse_args(
            self.window.core.config.get('llama.idx.storage.spec', []),
        )
        for key in kwargs_additional:
            if key in allowed_additional:
                spec_kwargs[key] = kwargs_additional[key]
        spec = ServerlessSpec(**spec_kwargs)

        # base idx create kwargs
        base_kwargs = {
            "name": id,
            "dimension": 1536,  # text-embedding-ada-002
            "metric": "euclidean",
            "spec": spec,
        }
        allowed_additional = ["name", "dimension", "metric"]
        kwargs_additional = parse_args(
            self.window.core.config.get('llama.idx.storage.args', []),
        )
        for key in kwargs_additional:
            if key in allowed_additional:
                base_kwargs[key] = kwargs_additional[key]

        pc = self.get_client()
        pc.create_index(**base_kwargs)

    def create(self, id: str):
        """
        Create index

        :param id: index name
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            # self.create_index(id=id)  # TODO: implement create option from UI
            os.makedirs(path)
            self.store(id)

    def get_client(self) -> Pinecone:
        """
        Get Pinecone client

        :return: Pinecone client
        """
        base_kwargs = {
            "api_key": "",
        }
        kwargs_additional = parse_args(
            self.window.core.config.get('llama.idx.storage.args', []),
        )
        if "api_key" in kwargs_additional:
            base_kwargs["api_key"] = kwargs_additional["api_key"]
        return Pinecone(**base_kwargs)  # api_key argument is required

    def get_store(self, id: str) -> PineconeVectorStore:
        """
        Get Pinecone store

        :param id: index name
        :return: PineconeVectorStore client
        """
        pc = self.get_client()
        name = id
        kwargs = parse_args(
            self.window.core.config.get('llama.idx.storage.args', []),
        )
        if "index_name" in kwargs:
            name = kwargs["index_name"]
        pinecone_index = pc.Index(name)  # use base index name or custom name
        return PineconeVectorStore(
            pinecone_index=pinecone_index,
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
        path = self.get_path(id)
        lock_file = os.path.join(path, 'store.lock')
        with open(lock_file, 'w') as f:
            f.write(id + ': ' + str(datetime.datetime.now()))
        self.indexes[id] = index

    def remove(self, id: str) -> bool:
        """
        Clear index

        :param id: index name
        :return: True if success
        """
        self.indexes[id] = None
        path = self.get_path(id)
        if os.path.exists(path):
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
            os.rmdir(path)
        return True

    def truncate(self, id: str) -> bool:
        """
        Truncate index

        :param id: index name
        :return: True if success
        """
        pc = self.get_client()
        pc.delete_index(id)
        return self.remove(id)

    def remove_document(self, id: str, doc_id: str) -> bool:
        """
        Remove document from index

        :param id: index name
        :param doc_id: document ID
        :return: True if success
        """
        index = self.get(id)
        index.delete(doc_id)
        self.store(
            id=id,
            index=index,
        )
        return True
