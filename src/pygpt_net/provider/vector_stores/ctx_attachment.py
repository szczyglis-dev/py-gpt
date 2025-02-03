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

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.base import BaseIndex

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

    def create(
            self, id: str,
            embed_model: Optional = None
    ):
        """
        Create empty index

        :param id: index name (not used)
        """
        path = self.get_path(id)
        if not os.path.exists(path):
            index = self.index_from_empty(embed_model)  # create empty index
            self.store(
                id=id,
                index=index,
            )
        else:
            self.index = self.index_from_empty(embed_model)

    def get(
            self,
            id: str,
            llm: Optional = None,
            embed_model: Optional = None,
    ) -> BaseIndex:
        """
        Get index

        :param id: index name (not used)
        :param llm: LLM instance
        :param embed_model: Embedding model instance
        :return: index instance
        """
        if not self.exists():
            self.create(id, embed_model)
        path = self.get_path(id)
        storage_context = StorageContext.from_defaults(
            persist_dir=path,
        )
        self.index = load_index_from_storage(
            storage_context,
            llm=llm,
            embed_model=embed_model,
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
