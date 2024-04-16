#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

import datetime
from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.core.index.base import BaseProvider
from pygpt_net.provider.core.index.json_file import JsonFileProvider
from pygpt_net.provider.core.index.db_sqlite import DbSqliteProvider
from pygpt_net.provider.vector_stores import Storage

from .indexing import Indexing
from .llm import Llm
from .chat import Chat
from .metadata import Metadata

from .types.ctx import Ctx
from .types.external import External
from .types.files import Files


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
        self.metadata = Metadata(window)

        self.providers = {
            "json_file": JsonFileProvider(window),  # only for patching
            "db_sqlite": DbSqliteProvider(window),
        }
        self.provider = "db_sqlite"
        self.items = {}
        self.initialized = False

        # internal types
        self.ctx = Ctx(window, self.get_provider())
        self.external = External(window, self.get_provider())
        self.files = Files(window, self.get_provider())

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
        Store (persist) index data

        :param idx: index name/ID
        """
        self.storage.store(idx)

    def remove_index(self, idx: str = "base", truncate: bool = False) -> bool:
        """
        Truncate index

        :param idx: index name
        :param truncate: truncate index (remove all data)
        :return: True if success
        """
        # get current store
        store = self.get_current_store()

        # clear db data
        self.ctx.truncate(store, idx)
        self.files.truncate(store, idx)

        # clear ctx data indexed status
        self.window.core.ctx.idx.truncate_indexed(store, idx)

        # clear storage, remove index
        if truncate:
            return self.storage.truncate(idx)
        else:
            return self.storage.remove(idx)

    def index_files(
            self,
            idx: str = "base",
            path: str = None,
            replace: bool = None,
            recursive: bool = None,
    ) -> (dict, list):
        """
        Index file or directory of files

        :param idx: index name
        :param path: path to file or directory
        :param replace: replace index
        :param recursive: recursive indexing
        :return: dict with indexed files (path -> id), list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            id=idx,
            service_context=context,
        )  # get or create index
        files, errors = self.indexing.index_files(
            idx=idx,
            index=index,
            path=path,
            replace=replace,
            recursive=recursive,
        )  # index files
        if len(files) > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index

        if errors:
            self.log("Error: " + str(errors))
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
            id=idx,
            service_context=context,
        )  # get or create index
        num, errors = self.indexing.index_db_by_meta_id(
            idx=idx,
            index=index,
            id=id,
            from_ts=from_ts,
        )  # index db records
        if num > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index

        if errors:
            self.log("Error: " + str(errors))
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
            id=idx,
            service_context=context,
        )  # get or create index
        num, errors = self.indexing.index_db_from_updated_ts(
            idx=idx,
            index=index,
            from_ts=from_ts,
        )  # index db records
        if num > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index

        if errors:
            self.log("Error: " + str(errors))
        return num, errors

    def index_urls(
            self,
            idx: str = "base",
            urls: list = None,
            type: str = "webpage",
            extra_args: dict = None
    ) -> (dict, list):
        """
        Index URLs

        :param idx: index name
        :param urls: list of urls
        :param type: type of url
        :param extra_args: extra args
        :return: num of indexed, list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(
            id=idx,
            service_context=context,
        )  # get or create index
        n, errors = self.indexing.index_urls(
            idx=idx,
            index=index,
            urls=urls,
            type=type,
            extra_args=extra_args,
        )  # index urls
        if n > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index

        if errors:
            self.log("Error: " + str(errors))
        return n, errors

    def index_web(
            self,
            idx: str = "base",
            type: str = "webpage",
            params: dict = None,
            config: dict = None,
            replace: bool = None,
    ) -> (dict, list):
        """
        Index URLs

        :param idx: index name
        :param type: type of url
        :param params: extra args
        :param config: extra config
        :param replace: replace index
        :return: num of indexed, list with errors
        """
        # update config params
        self.indexing.update_loader_args(type, config)

        context = self.llm.get_service_context()
        index = self.storage.get(
            id=idx,
            service_context=context,
        )  # get or create index
        n, errors = self.indexing.index_url(
            idx=idx,
            index=index,
            url="",
            type=type,
            extra_args=params,
            is_tmp=False,
            replace=replace,
        )
        if n > 0:
            self.storage.store(
                id=idx,
                index=index,
            )  # store index

        if errors:
            self.log("Error: " + str(errors))
        return n, errors

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
            file_id = self.files.get_id(path)
            ts = int(datetime.datetime.now().timestamp())
            if file_id not in self.items[store_id][idx].items:
                id = self.files.append(
                    store_id=store_id,
                    idx=idx,
                    file_id=file_id,
                    path=path,
                    doc_id=doc_id,
                )
                if id is not None:
                    self.items[store_id][idx].items[file_id] = {
                        "id": doc_id,
                        "db_id": id,  # DB id
                        "path": path,
                        "indexed_ts": ts,
                    }
            else:
                # update indexed timestamp only
                self.files.update(
                    id=self.items[store_id][idx].items[file_id]["db_id"],  # DB id
                    doc_id=doc_id,
                    ts=ts,
                )
                self.items[store_id][idx].items[file_id]["id"] = doc_id
                self.items[store_id][idx].items[file_id]["indexed_ts"] = ts

    def remove_doc(self, idx: str, doc_id: str):
        """
        Remove document from index

        :param idx: index name (id)
        :param doc_id: document ID (in storage)
        """
        self.llm.get_service_context()  # init environment only (ENV API keys, etc.)
        if self.storage.remove_document(idx, doc_id):
            self.log("Removed document from index: " + idx + " - " + doc_id)

    def remove_file(self, idx: str, file: str):
        """
        Remove file from index

        :param idx: index name
        :param file: file ID
        """
        self.llm.get_service_context()  # init environment only (ENV API keys, etc.)
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
                self.files.remove(store_id, idx, doc_id)

    def load(self):
        """Load indexes and indexed items"""
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

    def sync(self):
        """Sync idx items from config"""
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

    def get_idx_ids(self) -> list:
        """
        Get list of indexes

        :return: list of indexes
        """
        ids = []
        data =  self.window.core.config.get('llama.idx.list')
        if data is not None:
            for item in data:
                ids.append(item['id'])
        return ids

    def clear(self, idx: str):
        """
        Clear index items

        :param idx: index name/id
        """
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            self.items[store_id][idx].items = {}
        self.get_provider().truncate(store_id, idx)

    def get_counters(self, type: str) -> dict:
        """
        Get counters (stats, count items by type [file, ctx, external])

        :param type: type of counter (file, ctx, external)
        :return: dict of counters: [store][idx] -> count
        """
        return self.get_provider().get_counters(type)

    def get_version(self) -> str:
        """
        Get provider config version

        :return: provider config version
        """
        return self.get_provider().get_version()

    def log(self, msg: str):
        """
        Log info message

        :param msg: message
        """
        is_log = False
        if self.window.core.config.has("log.llama") \
                and self.window.core.config.get("log.llama"):
            is_log = True
        self.window.core.debug.info(msg, not is_log)
        if is_log:
            print("[LLAMA-INDEX] {}".format(msg))
        self.window.idx_logger_message.emit(msg)
