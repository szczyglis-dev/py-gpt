#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

from packaging.version import Version

from pygpt_net.provider.core.index.base import BaseProvider
from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "index"

    def attach(self, window):
        """
        Attach window to provider

        :param window: Window instance
        """
        self.window = window
        self.storage.attach(window)

    def patch(self, version: Version):
        """
        Patch versions

        :param version: current app version
        """
        return self.patcher.execute(version)

    def load(self, store_id: str) -> dict:
        """
        Load items for index provider

        :param store_id: store ID
        :return: dict of indexes and files in index
        """
        return self.storage.get_items(store_id)

    def append_file(self, store_id: str, idx: str, data: dict) -> int:
        """
        Append file to index

        :param: store_id: store ID
        :param: idx: index
        :param: data: dict of file data
        :return: ID of inserted file
        """
        return self.storage.insert_file(store_id, idx, data)

    def append_ctx_meta(self, store_id: str, idx: str, meta_id: int, doc_id: str) -> int:
        """
        Append context meta to index

        :param: store_id: store ID
        :param: idx: index
        :param: meta_id: context meta ID
        :param: doc_id: document ID
        :return: ID of inserted context meta
        """
        return self.storage.insert_ctx_meta(store_id, idx, meta_id, doc_id)

    def append_external(self, store_id: str, idx: str, data: dict) -> int:
        """
        Append external data to index

        :param: store_id: store ID
        :param: idx: index
        :param: data: dict of external data
        :return: ID of inserted external
        """
        return self.storage.insert_external(store_id, idx, data)

    def is_meta_indexed(self, store_id: str, idx: str, meta_id: int) -> bool:
        """
        Check if context meta is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: meta_id: context meta ID
        :return: True if indexed
        """
        return self.storage.is_meta_indexed(store_id, idx, meta_id)

    def is_file_indexed(self, store_id: str, idx: str, file_id: str) -> bool:
        """
        Check if file is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: file_id: file ID
        :return: True if indexed
        """
        return self.storage.is_file_indexed(store_id, idx, file_id)

    def is_external_indexed(self, store_id: str, idx: str, content: str, type: str) -> bool:
        """
        Check if external data is indexed

        :param: store_id: store ID
        :param: idx: index
        :param: content: external content
        :param: type: external type
        :return: True if indexed
        """
        return self.storage.is_external_indexed(store_id, idx, content, type)

    def get_meta_doc_id(self, store_id: str, idx: str, meta_id: int) -> str:
        """
        Get indexed document id by meta id

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: document id
        """
        return self.storage.get_meta_doc_id(store_id, idx, meta_id)

    def get_file_doc_id(self, store_id: str, idx: str, file_id: str) -> str:
        """
        Get indexed document id by file id

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :return: document id
        """
        return self.storage.get_file_doc_id(store_id, idx, file_id)

    def get_external_doc_id(self, store_id: str, idx: str, content: str, type: str) -> str:
        """
        Get indexed document id by file id

        :param store_id: store id
        :param idx: index name
        :param content: external content
        :param type: external type
        :return: document id
        """
        return self.storage.get_external_doc_id(store_id, idx, content, type)

    def update_file(self, id: int, doc_id: str, ts: int) -> bool:
        """
        Update indexed timestamp of indexed file

        :param: id: db record ID
        :param: doc_id: document ID
        :param: ts: timestamp
        """
        return self.storage.update_file(id, doc_id, ts)

    def update_ctx_meta(self, meta_id: int, doc_id: str) -> bool:
        """
        Update indexed timestamp of indexed context meta

        :param: meta_id: context meta ID
        :param: doc_id: document ID
        """
        return self.storage.update_ctx_meta(meta_id, doc_id)

    def update_external(self, content: str, type: str, doc_id: str, ts: int) -> bool:
        """
        Update indexed timestamp of indexed external

        :param: content: external content
        :param: type: external type
        :param: doc_id: document ID
        :param: ts: timestamp
        """
        return self.storage.update_external(content, type, doc_id, ts)

    def remove_file(self, store_id: str, idx: str, doc_id: str):
        """
        Remove file from index

        :param store_id: store ID
        :param idx: index
        :param doc_id: document ID
        """
        self.storage.remove_file(store_id, idx, doc_id)

    def remove_ctx_meta(self, store_id: str, idx: str, meta_id: str):
        """
        Remove file from index

        :param store_id: store ID
        :param idx: index
        :param meta_id: context meta ID
        """
        self.storage.remove_ctx_meta(store_id, idx, meta_id)

    def remove_external(self, store_id: str, idx: str, doc_id: str):
        """
        Remove external from index

        :param store_id: store ID
        :param idx: index
        :param doc_id: document ID
        """
        self.storage.remove_external(store_id, idx, doc_id)

    def truncate(self, store_id: str, idx: str) -> bool:
        """
        Truncate idx (remove all items)

        :param store_id: store ID
        :param idx: index
        :return: True if truncated
        """
        return self.storage.truncate_all(store_id, idx)

    def truncate_all(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate idx (remove all items) - all store and indexes

        :param store_id: store ID
        :param idx: index
        :return: True if truncated
        """
        return self.storage.truncate_all(store_id, idx)

    def truncate_files(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate files idx (remove all items) - all store and indexes

        :param store_id: store ID
        :param idx: index
        :return: True if truncated
        """
        return self.storage.truncate_files(store_id, idx)

    def truncate_ctx(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate context meta idx (remove all items) - all store and indexes

        :param store_id: store ID
        :param idx: index
        :return: True if truncated
        """
        return self.storage.truncate_ctx(store_id, idx)

    def truncate_external(self, store_id: str = None, idx: str = None) -> bool:
        """
        Truncate external idx (remove all items) - all store and indexes

        :param store_id: store ID
        :param idx: index
        :return: True if truncated
        """
        return self.storage.truncate_external(store_id, idx)

    def get_counters(self, type: str) -> dict:
        """
        Get counters (stats, count items by type [file, ctx, external])

        :param type: type of counter (file, ctx, external)
        :return: dict of counters
        """
        return self.storage.get_counters(type)
