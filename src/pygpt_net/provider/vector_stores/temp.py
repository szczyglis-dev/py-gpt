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

import os.path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.service_context import ServiceContext

from .base import BaseStore


class TempProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(TempProvider, self).__init__(*args, **kwargs)
        """
        Temporary vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = "TempVectorStore"
        self.prefix = ""  # prefix for index directory
        self.indexes = {}
        self.persist = False

    def count(self) -> int:
        """
        Count indexes

        :return: number of indexes
        """
        return len(self.indexes)

    def get_path(self, id: str) -> str:
        """
        Get database path

        :param id: index name
        :return: database path
        """
        if not self.persist:
            return ""

        tmp_dir = os.path.join(
            self.window.core.config.get_user_dir('idx'),
            "_tmp",  # temp directory
        )
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, exist_ok=True)
        path = os.path.join(
            self.window.core.config.get_user_dir('idx'),
            "_tmp",  # temp directory
            self.prefix + id,
        )
        return path

    def exists(self, id: str = None) -> bool:
        """
        Check if index with id exists

        :param id: index name
        :return: True if exists
        """
        if not self.persist:
            if id in self.indexes:
                return True
            return False

        path = self.get_path(id)
        if os.path.exists(path):
            store = os.path.join(path, "docstore.json")
            if os.path.exists(store):
                return True
        return False

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        if self.persist:
            path = self.get_path(id)
            if not os.path.exists(path):
                index = self.index_from_empty()  # create empty index
                self.store(
                    id=id,
                    index=index,
                )
        else:
            self.indexes[id] = self.index_from_empty()

    def get(self, id: str, service_context: ServiceContext = None) -> BaseIndex:
        """
        Get index

        :param id: tmp idx id
        :param service_context: Service context
        :return: index instance
        """
        if not self.exists(id):
            self.create(id)
        path = self.get_path(id)

        if self.persist:
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
        if not self.persist:
            self.indexes[id] = index
            return

        if index is None:
            index = self.indexes[id]
        path = self.get_path(id)
        index.storage_context.persist(
            persist_dir=path,
        )
        self.indexes[id] = index

    def clean(self, id: str):
        """
        Clean index

        :param id: index name
        """
        if not self.persist:
            if id in self.indexes:
                del self.indexes[id]
            return

        path = self.get_path(id)
        if os.path.exists(path):
            os.remove(path)
