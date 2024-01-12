#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 10:00:00                  #
# ================================================== #

import datetime
import os.path
from packaging.version import Version

from pygpt_net.item.index import IndexItem
from pygpt_net.provider.index.json_file import JsonFileProvider
from .indexing import Indexing
from .storage import Storage


class Idx:
    def __init__(self, window=None):
        """
        Indexers core

        :param window: Window instance
        """
        self.window = window
        self.indexing = Indexing(window)
        self.storage = Storage(window)
        self.provider = JsonFileProvider(window)
        self.items = {}
        self.initialized = False

    def store_index(self, idx: str = "base"):
        """
        Store index

        :param idx: Index name
        """
        self.storage.store(idx)

    def remove_index(self, idx: str = "base") -> bool:
        """
        Truncate index

        :param idx: Index name
        :return: True if success
        """
        return self.storage.remove(idx)

    def index(self, idx: str = "base", path: str = None, model: str = "gpt-3.5-turbo") -> tuple:
        """
        Index file or directory of files

        :param idx: Index name
        :param path: Path to file or directory
        :param model: Model used for indexing
        :return: dict with indexed files, errors
        """
        index = self.storage.get(idx, model=model)  # get or create index
        files, errors = self.indexing.index_files(index, path)  # index files
        if len(files) > 0:
            self.storage.store(id=idx, index=index)  # store index
        return files, errors

    def query(self, query, idx: str = "base", model: str = "gpt-3.5-turbo") -> str:
        """
        Query index

        :param query: Query string
        :param idx: Index name
        :param model: Model name
        :return: Response
        """
        if not self.storage.exists(idx):
            raise Exception("Index not prepared")
        index = self.storage.get(idx, model=model)  # get index
        response = index.as_query_engine().query(query)  # query index
        return str(response)  # TODO: handle stream response

    def get_idx_data(self, idx: str = "base") -> dict:
        """
        Get indexed files data
        :param idx: Index name
        :return: Indexed files data
        """
        if idx in self.items:
            return self.items[idx].items
        return {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version):
        """
        Patch provider data

        :param app_version: App version
        """
        self.provider.patch(app_version)

    def init(self):
        """Initialize indexes"""
        if not self.initialized:
            self.load()
            self.initialized = True

    def get(self, idx: str) -> IndexItem:
        """
        Return index data

        :param idx: index id
        :return: IndexItem object
        """
        if idx in self.items:
            return self.items[idx]

    def get_all(self) -> dict:
        """
        Return all indexes

        :return: all indexes
        """
        return self.items

    def has(self, idx: str) -> bool:
        """
        Check if index exists

        :param idx: index id
        :return: True if index exists
        """
        return idx in self.items

    def is_indexed(self, idx: str, file: str) -> bool:
        """
        Check if file is indexed

        :param idx: index id
        :param file: file path
        :return: True if file is indexed
        """
        if idx in self.items:
            return file in self.items[idx].items
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

        :param idx: index id
        :param files: dict of indexed files
        """
        if idx in self.items:
            for path in files:
                file = files[path]
                file_id = self.to_file_id(path)
                self.items[idx].items[file_id] = {
                    "path": path,
                    "indexed_ts": datetime.datetime.now().timestamp(),
                    "id": file,
                }
            self.save()

    def clear(self, idx: str):
        """
        Clear index items

        :param idx: index id
        """
        if idx in self.items:
            self.items[idx].items = {}
            self.save()

    def load(self):
        """
        Load indexes
        """
        self.items = self.provider.load()

    def save(self):
        """Save indexes"""
        self.provider.save(self.items)

    def get_version(self) -> str:
        """
        Get config version

        :return: config version
        """
        return self.provider.get_version()
