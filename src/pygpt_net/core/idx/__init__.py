#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 01:00:00                  #
# ================================================== #

import datetime
import os.path
from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.core.index.base import BaseProvider
from pygpt_net.provider.core.index.json_file import JsonFileProvider
from pygpt_net.provider.core.index.db_sqlite import DbSqliteProvider
from pygpt_net.provider.vector_stores import Storage

from .indexing import Indexing
from .llm import Llm
from .chat import Chat


class Idx:
    def __init__(self, window=None):
        """
        Indexer core

        :param window: Window instance
        """
        self.window = window
        self.indexing = Indexing(window)
        self.llm = Llm(window)
        self.storage = Storage(window)
        self.chat = Chat(window, self.storage)
        self.providers = {
            "json_file": JsonFileProvider(window),  # only for patching
            "db_sqlite": DbSqliteProvider(window),
        }
        self.provider = "db_sqlite"
        self.items = {}
        self.initialized = False

    def get_current_store(self) -> str:
        """
        Get current vector store name/ID

        :return: vector store name
        """
        return self.window.core.config.get('llama.idx.storage')

    def get_provider(self) -> BaseProvider:
        """
        Get provider instance

        :return: provider instance
        """
        return self.providers.get(self.provider)

    def store_index(self, idx: str = "base"):
        """
        Store index

        :param idx: index name
        """
        self.storage.store(idx)

    def remove_index(self, idx: str = "base", truncate: bool = False) -> bool:
        """
        Truncate index

        :param idx: index name
        :param truncate: truncate index
        :return: True if success
        """
        # get current store
        store = self.get_current_store()

        # clear db data
        self.truncate_ctx_db(store, idx)
        self.truncate_files_db(store, idx)

        # clear ctx data indexed status
        self.window.core.ctx.truncate_indexed(store, idx)

        # clear storage, remove index
        if truncate:
            return self.storage.truncate(idx)
        else:
            return self.storage.remove(idx)

    def index_files(
            self,
            idx: str = "base",
            path: str = None
    ) -> (dict, list):
        """
        Index file or directory of files

        :param idx: index name
        :param path: path to file or directory
        :return: dict with indexed files (path -> id), list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            idx,
            service_context=context,
        )  # get or create index
        files, errors = self.indexing.index_files(
            idx,
            index,
            path,
        )  # index files
        if len(files) > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index
        return files, errors

    def index_db_by_meta_id(
            self,
            idx: str = "base",
            id: int = 0,
            from_ts: int = 0
    ) -> (int, list):
        """
        Index records from db by meta id

        :param idx: index name
        :param id: CtxMeta id
        :param from_ts: timestamp from
        :return: num of indexed files, list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            idx,
            service_context=context,
        )  # get or create index
        num, errors = self.indexing.index_db_by_meta_id(
            idx,
            index,
            id,
            from_ts,
        )  # index db records
        if num > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index
        return num, errors

    def index_db_from_updated_ts(
            self,
            idx: str = "base",
            from_ts: int = 0
    ) -> (int, list):
        """
        Index records from db by meta id

        :param idx: index name
        :param from_ts: timestamp from
        :return: num of indexed files, list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            idx,
            service_context=context,
        )  # get or create index
        num, errors = self.indexing.index_db_from_updated_ts(
            idx,
            index,
            from_ts,
        )  # index db records
        if num > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index
        return num, errors

    def index_urls(
            self,
            idx: str = "base",
            urls: list = None,
    ) -> (dict, list):
        """
        Index URLs

        :param idx: index name
        :param urls: list of urls
        :return: num of indexed, list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            idx,
            service_context=context,
        )  # get or create index
        n, errors = self.indexing.index_urls(
            index,
            urls,
        )  # index urls
        if n > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index
        return n, errors

    def sync_items(self):
        """Sync from config"""
        items = self.window.core.config.get('llama.idx.list')
        store_id = self.get_current_store()
        if items is not None:
            if store_id not in self.items:
                self.items[store_id] = {}
            for item in items:
                idx = item['id']
                if idx not in self.items[store_id]:
                    self.items[store_id][idx] = IndexItem()
                    self.items[store_id][idx].id = idx
                    self.items[store_id][idx].name = idx
                    self.items[store_id][idx].store = store_id
                else:
                    self.items[store_id][idx].id = idx
                    self.items[store_id][idx].name = idx

    def get_idx_data(self, idx: str = None) -> dict:
        """
        Get indexed files data

        :param idx: index name
        :return: indexed files data (idx -> items)
        """
        indexes = {}
        store_id = self.get_current_store()
        if idx is not None:
            if store_id in self.items and idx in self.items[store_id]:
                indexes[idx] = self.items[store_id][idx].items
        else:
            # all indexes
            if store_id in self.items:
                for idx in self.items[store_id]:
                    indexes[idx] = self.items[store_id][idx].items
        return indexes

    def get_by_idx(self, idx: int) -> str:
        """
        Return idx by list index

        :param idx: idx on list
        :return: idx name
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            if idx < len(items):
                return items[idx]['id']

    def get_idx_by_name(self, name: str) -> int:
        """
        Return idx on list by name

        :param name: idx name
        :return: idx on list
        """
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            for idx, item in enumerate(items):
                if item['id'] == name:
                    return idx

    def get_default_idx(self) -> str:
        """
        Return default idx

        :return: idx name
        """
        if len(self.items) > 0:
            return self.get_by_idx(0)

    def install(self):
        """Install provider data"""
        self.get_provider().install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if success
        """
        return self.get_provider().patch(app_version)

    def init(self):
        """Initialize indexes"""
        if not self.initialized:
            self.load()
            self.initialized = True

    def get(self, idx: str) -> IndexItem:
        """
        Return index data from current storage

        :param idx: index name
        :return: IndexItem object
        """
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            return self.items[store_id][idx]

    def get_all(self) -> dict:
        """
        Return all indexes in current store

        :return: all indexes
        """
        store_id = self.get_current_store()
        if store_id in self.items:
            return self.items[store_id]
        return {}

    def get_idx_config(self, idx: str) -> dict:
        """
        Return index config

        :param idx: index name
        :return: index config
        """
        indexes = self.window.core.config.get('llama.idx.list')
        if indexes is not None:
            for item in indexes:
                if item['id'] == idx:
                    return item

    def has(self, idx: str) -> bool:
        """
        Check if index exists

        :param idx: index name
        :return: True if index exists
        """
        store_id = self.get_current_store()
        if store_id in self.items:
            return idx in self.items[store_id]
        return False

    def is_indexed(self, idx: str, file: str) -> bool:
        """
        Check if file is indexed

        :param idx: index name
        :param file: file path
        :return: True if file is indexed
        """
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            return file in self.items[store_id][idx].items
        return False

    def remove_file_from_index(self, idx: str, file: str):
        """
        Remove file from index

        :param idx: index name
        :param file: file ID
        """
        self.llm.get_service_context()  # init environment only (API keys, etc.)
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            if file in self.items[store_id][idx].items:
                # remove from storage
                doc_id = self.items[store_id][idx].items[file]["id"]
                self.storage.remove_document(
                    id=idx,
                    doc_id=doc_id,
                )
                # remove from index data and db
                del self.items[store_id][idx].items[file]
                self.remove_file(store_id, idx, doc_id)

    def remove_doc_from_index(self, idx: str, doc_id: str):
        """
        Remove file from index

        :param idx: index name
        :param doc_id: file ID
        """
        self.llm.get_service_context()  # init environment only (API keys, etc.)
        if self.storage.remove_document(idx, doc_id):
            self.indexing.log("Removed document from index: " + idx + " - " + doc_id)

    def to_file_id(self, path: str) -> str:
        """
        Prepare file id

        :param path: file path
        :return: file id
        """
        path = os.path.normpath(path)
        root_path = os.path.normpath(self.window.core.config.get_user_dir('data'))
        path = path.replace(root_path, '')
        path = path.replace("\\", "/").strip(r'\/')
        return path

    def append(self, idx: str, files: dict):
        """
        Append indexed files to index

        :param idx: index name
        :param files: dict of indexed files
        """
        # create store if not exists
        store_id = self.get_current_store()
        if store_id not in self.items:
            self.items[store_id] = {}

        # create index if not exists
        if idx not in self.items[store_id]:
            self.items[store_id][idx] = IndexItem()
            self.items[store_id][idx].id = idx
            self.items[store_id][idx].name = idx  # use index id as name

        # append indexed files
        for path in files:
            doc_id = files[path]
            file_id = self.to_file_id(path)
            ts = int(datetime.datetime.now().timestamp())
            if file_id not in self.items[store_id][idx].items:
                id = self.append_file(
                    store_id=store_id,
                    idx=idx,
                    file_id=file_id,
                    path=path,
                    doc_id=doc_id,
                )
                if id is not None:
                    self.items[store_id][idx].items[file_id] = {
                        "id": doc_id,
                        "db_id": id,
                        "path": path,
                        "indexed_ts": ts,
                    }
            else:
                # update indexed timestamp only
                self.update_file(
                    self.items[store_id][idx].items[file_id]["db_id"],
                    doc_id,
                    ts,
                )
                self.items[store_id][idx].items[file_id]["id"] = doc_id
                self.items[store_id][idx].items[file_id]["indexed_ts"] = ts

    def clear(self, idx: str):
        """
        Clear index items

        :param idx: index name
        """
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            self.items[store_id][idx].items = {}
        self.get_provider().truncate(store_id, idx)

    def load(self):
        """Load indexes"""
        store_ids = self.storage.get_ids()
        for store_id in store_ids:
            self.items[store_id] = self.get_provider().load(store_id)
            # replace workdir placeholder with current workdir
            for idx in self.items[store_id]:
                for id in self.items[store_id][idx].items:
                    file = self.items[store_id][idx].items[id]
                    if 'path' in file and file['path'] is not None:
                        self.items[store_id][idx].items[id]['path'] = \
                            self.window.core.filesystem.to_workdir(file['path'])

    def append_file(
            self,
            store_id: str,
            idx: str,
            file_id: str,
            path: str,
            doc_id: str
    ) -> int:
        """
        Append file to index

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :param path: file path
        :param doc_id: document id
        :return: ID of appended file
        """
        data = {
            "name": file_id,  # use file id as name
            "path": path,
            "indexed_ts": datetime.datetime.now().timestamp(),
            "id": doc_id,
        }
        return self.get_provider().append_file(store_id, idx, data)

    def update_file(self, id: int, doc_id: str, ts: int) -> bool:
        """
        Update timestamp of indexed file

        :param id: record ID
        :param doc_id: document ID
        :param ts: timestamp
        :return: True if file was updated
        """
        return self.get_provider().update_file(id, doc_id, ts)

    def remove_file(self, store_id: str, idx: str, doc_id: str):
        """
        Remove document from index

        :param store_id: store id
        :param idx: index name
        :param doc_id: document id
        """
        self.get_provider().remove_file(store_id, idx, doc_id)

    def is_file_indexed(self, store_id: str, idx: str, file_id: str) -> bool:
        """
        Check if file is indexed

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :return: True if ctx meta is indexed
        """
        return self.get_provider().is_file_indexed(store_id, idx, file_id)

    def is_meta_indexed(self, store_id: str, idx: str, meta_id: int) -> bool:
        """
        Check if ctx meta is indexed

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: True if ctx meta is indexed
        """
        return self.get_provider().is_meta_indexed(store_id, idx, meta_id)

    def get_meta_doc_id(self, store_id: str, idx: str, meta_id: int) -> str:
        """
        Get indexed document id by meta id

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: document id
        """
        return self.get_provider().get_meta_doc_id(store_id, idx, meta_id)

    def get_file_doc_id(self, store_id: str, idx: str, file_id: str) -> str:
        """
        Get indexed document id by file

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :return: document id
        """
        return self.get_provider().get_file_doc_id(store_id, idx, file_id)

    def append_ctx_meta(
            self,
            store_id: str,
            idx: str,
            meta_id: int,
            doc_id: str
    ) -> int:
        """
        Append ctx meta to index

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :param doc_id: document id
        :return: ID of appended ctx meta
        """
        return self.get_provider().append_ctx_meta(store_id, idx, meta_id, doc_id)

    def update_ctx_meta(self, meta_id: int, doc_id: str) -> bool:
        """
        Update timestamp of indexed ctx meta

        :param meta_id: ctx meta id
        :param doc_id: document id
        :return: True if file was updated
        """
        return self.get_provider().update_ctx_meta(meta_id, doc_id)

    def remove_ctx_meta(self, store_id: str, idx: str, meta_id: str):
        """
        Remove document from index

        :param store_id: store id
        :param idx: index name
        :param meta_id: ctx meta id
        """
        self.get_provider().remove_ctx_meta(store_id, idx, meta_id)

    def truncate_ctx_db(self, store_id: str = None, idx: str = None):
        """
        Truncate ctx meta from index

        :param store_id: store id
        :param idx: index name
        """
        self.get_provider().truncate_ctx_db(store_id, idx)

    def truncate_files_db(self, store_id: str = None, idx: str = None):
        """
        Truncate files from index

        :param store_id: store id
        :param idx: index name
        """
        self.get_provider().truncate_files_db(store_id, idx)

    def get_version(self) -> str:
        """
        Get config version

        :return: config version
        """
        return self.get_provider().get_version()
