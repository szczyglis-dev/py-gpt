#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT LlamaIndex vector-store tutorial             #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

import os
from typing import Optional

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.indices.base import BaseIndex

from pygpt_net.provider.vector_stores.base import BaseStore


class ExampleVectorStore(BaseStore):
    """A disk-persisted vector-store provider based on PyGPT's SimpleProvider.

    The important current API detail is that `get()` receives `llm` and
    `embed_model` directly. Older examples used LlamaIndex `ServiceContext`,
    which is no longer the interface used by PyGPT.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "ExampleVectorStore"  # unique provider ID shown in settings
        self.prefix = "example_"  # directory prefix below workdir/idx

    def create(
        self,
        id: str,
        embed_model: Optional = None,
    ):
        """Create and persist an empty index if it does not already exist."""
        path = self.get_path(id)
        if os.path.exists(path):
            return

        # BaseStore knows how to create the current VectorStoreIndex shape.
        index = self.index_from_empty(embed_model)
        self.store(id=id, index=index)

    def get(
        self,
        id: str,
        llm: Optional = None,
        embed_model: Optional = None,
    ) -> BaseIndex:
        """Load an index and bind the LLM/embedding instances supplied by PyGPT."""
        if not self.exists(id):
            self.create(id, embed_model)

        storage_context = StorageContext.from_defaults(
            persist_dir=self.get_path(id),
        )
        index = load_index_from_storage(
            storage_context,
            llm=llm,
            embed_model=embed_model,
        )
        self.indexes[id] = index
        return index

    def store(
        self,
        id: str,
        index: Optional[BaseIndex] = None,
    ):
        """Persist an index under workdir/idx/<prefix><id>."""
        if index is None:
            index = self.indexes[id]

        index.storage_context.persist(
            persist_dir=self.get_path(id),
        )
        self.indexes[id] = index

    # `exists()`, `remove()`, `truncate()`, `remove_document()`, `attach()` and
    # `get_path()` are already implemented by BaseStore and normally do not need
    # to be copied into a custom provider.
