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

import hashlib
from typing import Optional, Tuple, List

from llama_index.core.indices.base import BaseIndex
from llama_index.core.indices.vector_store.base import VectorStoreIndex

from .base import BaseStore
from .ctx_attachment import CtxAttachmentProvider
from .temp import TempProvider


class Storage:
    def __init__(self, window=None):
        """
        Storage handler

        :param window: Window instance
        """
        self.window = window
        self.storages = {}
        self.indexes = {}
        self.tmp_storage = TempProvider(window=window)

    def get_storage(self) -> Optional[BaseStore]:
        """
        Get current vector store provider

        :return: vector store provider instance
        """
        current = self.window.core.config.get("llama.idx.storage")
        if current is None \
                or current == "_" \
                or current not in self.storages:
            return None
        return self.storages[current]

    def get_tmp_storage(self) -> Optional[TempProvider]:
        """
        Get temp vector store provider

        :return: vector store provider instance
        """
        return self.tmp_storage

    def get_ctx_idx_storage(self, path: str) -> CtxAttachmentProvider:
        """
        Get temp vector store provider
        
        :param path: Path to index on disk
        :return: vector store provider instance
        """
        return CtxAttachmentProvider(
            window=self.window,
            path=path
        )

    def register(self, name: str, storage: BaseStore):
        """
        Register vector store provider

        :param name: vector store provider name (ID)
        :param storage: vector store provider instance
        """
        storage.attach(window=self.window)
        self.storages[name] = storage

    def get_ids(self) -> List[str]:
        """
        Return all vector store providers IDs

        :return: list of vector store providers (IDs)
        """
        return list(self.storages.keys())

    def exists(self, id: Optional[str] = None) -> bool:
        """
        Check if index exists

        :param id: index name
        :return: True if exists
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.exists(id)

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.create(id)

    def get(
            self,
            id: str,
            llm: Optional = None,
            embed_model: Optional = None,
    ) -> BaseIndex:
        """
        Get index instance

        :param id: index name
        :param llm: LLM instance
        :param embed_model: Embedding model instance
        :return: index instance
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.get(
            id=id,
            llm=llm,
            embed_model=embed_model,
        )

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
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.store(
            id=id,
            index=index,
        )

    def remove(self, id: str) -> bool:
        """
        Clear index only

        :param id: index name
        :return: True if success
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.remove(id)

    def truncate(self, id: str) -> bool:
        """
        Truncate and clear index

        :param id: index name
        :return: True if success
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.truncate(id)

    def remove_document(self, id: str, doc_id: str) -> bool:
        """
        Remove document from index

        :param id: index name
        :param doc_id: document ID
        :return: True if success
        """
        storage = self.get_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.remove_document(
            id=id,
            doc_id=doc_id,
        )

    def get_tmp(
            self,
            identifier: str,
            llm: Optional = None,
            embed_model: Optional = None,
    ) -> Tuple[str, BaseIndex]:
        """
        Get tmp index instance

        :param identifier: identifier
        :param llm: LLM instance
        :param embed_model: Embedding model instance
        :return: index instance
        """
        # convert path to md5 hash
        id = hashlib.md5(identifier.encode()).hexdigest()
        storage = self.get_tmp_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return id, storage.get(
            id=id,
            llm=llm,
            embed_model=embed_model,
        )

    def store_tmp(
            self,
            id: str,
            index: Optional[BaseIndex] = None
    ):
        """
        Store index

        :param id: index name
        :param index: index instance
        """
        storage = self.get_tmp_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.store(
            id=id,
            index=index,
        )

    def count_tmp(self) -> int:
        """
        Count temp indices

        :return: number of temp indices
        """
        storage = self.get_tmp_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.count()

    def clean_tmp(self, id: str):
        """
        Clean temp index

        :param id: index name
        """
        storage = self.get_tmp_storage()
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.clean(id)

    def get_ctx_idx(
            self,
            path: str,
            llm: Optional = None,
            embed_model: Optional = None,
    ) -> BaseIndex:
        """
        Get context index instance

        :param path: path to index directory
        :param llm: LLM instance
        :param embed_model: Embedding model instance
        :return: index instance
        """
        # convert path to md5 hash
        storage = self.get_ctx_idx_storage(path)
        if storage is None:
            raise Exception('Storage engine not found!')
        return storage.get(
            id="",
            llm=llm,
            embed_model=embed_model,
        )

    def store_ctx_idx(
            self,
            path: str,
            index: Optional[BaseIndex] = None
    ):
        """
        Store context index

        :param path: path to index directory
        :param index: index instance
        """
        storage = self.get_ctx_idx_storage(path)
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.store(
            id="",
            index=index,
        )

    def clean_ctx_idx(self, path: str):
        """
        Clean temp index

        :param path: path to index directory
        """
        storage = self.get_ctx_idx_storage(path)
        if storage is None:
            raise Exception('Storage engine not found!')
        storage.clean()

    def index_from_empty(
            self,
            embed_model: Optional = None) -> BaseIndex:
        """
        Create empty index

        :return: index instance
        """
        return VectorStoreIndex(
            [],
            embed_model=embed_model,
        )
