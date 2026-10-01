"""Runnable persistent vector-store provider based on LlamaIndex local storage."""

from typing import Optional

from pygpt_net.provider.vector_stores.base import BaseStore


class ExampleVectorStore(BaseStore):
    def __init__(self):
        super().__init__()
        self.id = "ExampleSimpleVectorStore"
        # Every index created through this provider gets its own prefixed folder
        # under the normal PyGPT idx directory.
        self.prefix = "example_"

    def create(self, id: str, embed_model=None):
        if self.exists(id):
            return
        index = self.index_from_empty(embed_model=embed_model)
        self.store(id, index)

    def get(self, id: str, llm=None, embed_model=None):
        from llama_index.core import StorageContext, load_index_from_storage

        if not self.exists(id):
            self.create(id, embed_model=embed_model)
        storage_context = StorageContext.from_defaults(persist_dir=self.get_path(id))
        index = load_index_from_storage(
            storage_context,
            llm=llm,
            embed_model=embed_model,
        )
        self.indexes[id] = index
        return index

    def store(self, id: str, index: Optional[object] = None):
        index = index or self.indexes[id]
        index.storage_context.persist(persist_dir=self.get_path(id))
        self.indexes[id] = index
