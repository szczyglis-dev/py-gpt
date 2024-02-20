#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.20 02:00:00                  #
# ================================================== #

import os.path
from llama_index.indices.base import BaseIndex
from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
    load_index_from_storage,
)

from pygpt_net.provider.vector_stores.base import BaseStore  # <--- vector store must inherit from BaseStore


class ExampleVectorStore(BaseStore):
    def __init__(self, *args, **kwargs):
        super(ExampleVectorStore, self).__init__(*args, **kwargs)
        """
        Example vector store provider.
        
        This example is based on the `SimpleProvider` (SimpleVectorStore) from the `pygpt_net.provider.vector_stores.simple`.
        See `pygpt_net.provider.vector_stores` for more examples.

        The rest of the shared methods (like `exists`, `delete`, `truncate`, etc.) are declared in the base class: `BaseStore`.

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "example_store"  # identifier must be unique
        self.prefix = "example_"  # prefix for index config files subdirectory in "idx" directory in %workdir%
        self.indexes = {}  # indexes cache dictionary (in-memory)

    def create(self, id: str):
        """
        Create the empty index with the provided `id` (`base` is default)

        In this example, we create an empty index with the name `id` and store it in the `self.indexes` dictionary.
        Example is a simple copy of the `SimpleVectorStore` provider.
        The `create` method is called when the index does not exist.

        See `pygpt_net.core.idx` for more details how it is handled internally.

        :param id: index name
        """
        path = self.get_path(id)  # get path for the index configuration, declared in the `BaseStore` class

        # check if index does not exist on disk and create it if not exists
        if not os.path.exists(path):
            index = VectorStoreIndex([])  # create empty index

            # store the index on disk
            self.store(
                id=id,
                index=index,
            )

    def get(self, id: str, service_context: ServiceContext = None) -> BaseIndex:
        """
        Get the index instance with the provided `id` (`base` is default)

        In this example, we get the index with the name `id` from the `self.indexes` dictionary.
        The `get` method is called when getting the index instance.
        It must return the `BaseIndex` index instance.

        See `pygpt_net.core.idx` for more details how it is handled internally.

        :param id: index name
        :param service_context: Service context
        :return: index instance
        """

        # check if index exists on disk and load it
        if not self.exists(id):
            # if index does not exist, then create it
            self.create(id)

        # get path for the index configuration on disk (in "%workdir%/idx" directory)
        path = self.get_path(id)

        # get the storage context
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
        )

        # load index from storage and update it in the `self.indexes` dictionary
        self.indexes[id] = load_index_from_storage(
            storage_context,
            service_context=service_context,
        )

        # return the index instance
        return self.indexes[id]

    def store(self, id: str, index: BaseIndex = None):
        """
        Store (persist) the index instance with the provided `id` (`base` is default)

        In this example, we store the index with the name `id` in the `self.indexes` dictionary.
        The `store` method is called when storing (persisting) index to disk/db.
        It must provide logic to store the index in the storage.

        See `pygpt_net.core.idx` for more details how it is handled internally.

        :param id: index name
        :param index: index instance
        """

        # prepare the index instance
        if index is None:
            index = self.indexes[id]

        # get a path for the index configuration on disk (in "%workdir%/idx" directory)
        path = self.get_path(id)

        # persist the index on disk
        index.storage_context.persist(
            persist_dir=path,
        )

        # update the index in the `self.indexes` dictionary
        self.indexes[id] = index
