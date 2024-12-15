#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import os.path
from typing import Optional

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.service_context import ServiceContext

from .base import BaseStore


class CtxAttachmentProvider(BaseStore):
    def __init__(self, *args, **kwargs):
        super(CtxAttachmentProvider, self).__init__(*args, **kwargs)
        """
        Context attachments vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.path = kwargs.get("path", None)
        self.id = "CtxAttachmentVectorStore"
        self.index = None

    def get_path(self, id: str) -> str:
        """
        Get database path

        :return: database path
        """
        return self.path

    def exists(
            self,
            id: Optional[str] = None
    ) -> bool:
        """
        Check if index exists

        :return: True if exists
        """
        path = self.get_path("")
        if os.path.exists(path):
            store = os.path.join(path, "docstore.json")
            if os.path.exists(store):
                return True
        return False

    def create(self, id: str):
        """
        Create empty index

        :param id: index name (not used)
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            index = self.index_from_empty()  # create empty index
            self.store(
                id=id,
                index=index,
            )
        else:
            self.index = self.index_from_empty()

    def get(
            self,
            id: str,
            service_context: Optional[ServiceContext] = None
    ) -> BaseIndex:
        """
        Get index

        :param id: index name (not used)
        :param service_context: Service context
        :return: index instance
        """
        if not self.exists():
            self.create(id)
        path = self.get_path(id)
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
        )
        self.index = load_index_from_storage(
            storage_context,
            service_context=service_context,
        )

        return self.index

    def store(
            self,
            id: str,
            index: Optional[BaseIndex] = None
    ):
        """
        Store index

        :param id: index name (not used)
        :param index: index instance
        """
        path = self.get_path(id)
        index.storage_context.persist(
            persist_dir=path,
        )
        self.index = index

    def clean(self):
        """Clean index"""
        self.index = None
        path = self.get_path("")
        if os.path.exists(path):
            os.remove(path)
