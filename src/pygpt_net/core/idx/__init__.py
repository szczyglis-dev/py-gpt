#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 16:00:00                  #
# ================================================== #

import copy
import datetime
import os.path
from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.core.index.json_file import JsonFileProvider
from pygpt_net.provider.vector_stores import Storage

from .indexing import Indexing
from .llm import Llm
from .chat import Chat


class Idx:
    def __init__(self, window=None):
        """
        Indexers core

        :param window: Window instance
        """
        self.window = window
        self.indexing = Indexing(window)
        self.llm = Llm(window)
        self.storage = Storage(window)
        self.chat = Chat(window, self.storage)
        self.provider = JsonFileProvider(window)
        self.items = {}
        self.initialized = False

    def get_current_store(self) -> str:
        """
        Get current vector store name/ID

        :return: vector store name
        """
        return self.window.core.config.get('llama.idx.storage')

    def store_index(self, idx: str = "base"):
        """
        Store index

        :param idx: index name
        """
        self.storage.store(idx)

    def remove_index(self, idx: str = "base") -> bool:
        """
        Truncate index

        :param idx: index name
        :return: True if success
        """
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
        index = self.storage.get(idx, service_context=context)  # get or create index
        files, errors = self.indexing.index_files(index, path)  # index files
        if len(files) > 0:
            self.storage.store(id=idx, index=index)  # store index
        return files, errors

    def index_db_by_meta_id(
            self,
            idx: str = "base",
            id: int = 0
    ) -> (int, list):
        """
        Index records from db by meta id

        :param idx: index name
        :param id: CtxMeta id
        :return: num of indexed files, list with errors
        """
        context = self.llm.get_service_context()
        index = self.storage.get(idx, service_context=context)  # get or create index
        num, errors = self.indexing.index_db_by_meta_id(index, id)  # index db records
        if num > 0:
            self.storage.store(id=idx, index=index)  # store index
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
        index = self.storage.get(idx, service_context=context)  # get or create index
        num, errors = self.indexing.index_db_from_updated_ts(index, from_ts)  # index db records
        if num > 0:
            self.storage.store(id=idx, index=index)  # store index
        return num, errors

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
            self.save()

    def get_idx_data(self, idx: str = None) -> dict:
        """
        Get indexed files data

        :param idx: index name
        :return: indexed files data
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
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if success
        """
        return self.provider.patch(app_version)

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
        store_id = self.get_current_store()
        if store_id not in self.items:
            self.items[store_id] = {}
        if idx not in self.items[store_id]:
            self.items[store_id][idx] = IndexItem()
            self.items[store_id][idx].id = idx
            self.items[store_id][idx].name = idx  # use index id as name

        for path in files:
            file = files[path]
            file_id = self.to_file_id(path)
            self.items[store_id][idx].items[file_id] = {
                "path": path,
                "indexed_ts": datetime.datetime.now().timestamp(),
                "id": file,
            }
        self.save()

    def clear(self, idx: str):
        """
        Clear index items

        :param idx: index name
        """
        store_id = self.get_current_store()
        if store_id in self.items and idx in self.items[store_id]:
            self.items[store_id][idx].items = {}
            self.save()

    def load(self):
        """Load indexes"""
        self.items = self.provider.load()
        # replace workdir placeholder with current workdir
        for store_id in self.items:
            for idx in self.items[store_id]:
                for id in self.items[store_id][idx].items:
                    file = self.items[store_id][idx].items[id]
                    if 'path' in file and file['path'] is not None:
                        self.items[store_id][idx].items[id]['path'] = \
                            self.window.core.filesystem.to_workdir(file['path'])

    def save(self):
        """Save indexes"""
        data = self.make_save_data(self.items)
        self.provider.save(data)

    def make_save_data(self, items: dict) -> dict:
        """
        Make data for save

        :param items: indexes data
        :return: data for save
        """
        data = copy.deepcopy(items)
        # replace workdir with placeholder
        for store_id in data:
            for idx in data[store_id]:
                for file_id in data[store_id][idx].items:
                    file = data[store_id][idx].items[file_id]
                    if 'path' in file and file['path'] is not None:
                        data[store_id][idx].items[file_id]['path'] = \
                            self.window.core.filesystem.make_local(file['path'])
        return data

    def get_version(self) -> str:
        """
        Get config version

        :return: config version
        """
        return self.provider.get_version()
