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

import datetime
import os.path

from pinecone import Pinecone, ServerlessSpec

from llama_index.core import StorageContext
from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.service_context import ServiceContext
from llama_index.vector_stores.pinecone import PineconeVectorStore

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
        self.prefix = "pinecode_"  # prefix for index directory
        self.indexes = {}

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
        self.indexes[id] = self.index_from_store(vector_store, storage_context, service_context)
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

    def truncate(self, id: str) -> bool:
        """
        Truncate index

        :param id: index name
        :return: True if success
        """
        pc = self.get_client()
        pc.delete_index(id)
        return self.remove(id)
