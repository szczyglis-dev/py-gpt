#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

import os
import time
from typing import Optional, List, Dict, Any

from pygpt_net.item.store import RemoteStoreItem

from .worker.importer import Importer

class Store:
    def __init__(self, window=None):
        """
        Google (Gemini) File Search stores API wrapper

        :param window: Window instance
        """
        self.window = window
        self.importer = Importer(window)

    def get_client(self):
        """
        Get Google GenAI client

        :return: google.genai.Client
        """
        return self.window.core.api.google.get_client()

    def log(self, msg: str, callback: Optional[callable] = None):
        """
        Log message

        :param msg: message to log
        :param callback: callback log function
        """
        if callback is not None:
            callback(msg)
        else:
            print(msg)

    # -----------------------------
    # helpers
    # -----------------------------

    def _clamp(self, val: int, lo: int, hi: int) -> int:
        """Clamp integer value into range [lo, hi]."""
        try:
            v = int(val or 0)
        except Exception:
            v = lo
        if v < lo:
            v = lo
        if v > hi:
            v = hi
        return v

    # -----------------------------
    # Files service (global)
    # -----------------------------

    def get_file(self, file_name: str):
        """
        Get Files API file metadata by name (e.g. 'files/abc-123').

        :param file_name: Files API resource name
        :return: file metadata
        """
        client = self.get_client()
        return client.files.get(name=file_name)

    def upload(self, path: str) -> Optional[str]:
        """
        Upload file to Files API (not to a File Search Store). Use when you want to import later.

        :param path: file path
        :return: Files API resource name (e.g., 'files/abc-123') or None
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        cfg = {'name': os.path.basename(path)}
        res = client.files.upload(file=path, config=cfg)
        if res is not None and hasattr(res, "name"):
            return res.name

    def delete_file(self, file_name: str) -> Optional[str]:
        """
        Delete file from Files API

        :param file_name: Files API resource name ('files/...').
        :return: file_name if removed
        """
        client = self.get_client()
        res = client.files.delete(name=file_name)
        if res is not None:
            return file_name

    def get_files_ids_all(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all Files API file names (paginated)

        :param items: items accumulator
        :param order: unused, for compatibility
        :param limit: page size (max 100 for Files API)
        :param after: page token
        :return: file names list
        """
        client = self.get_client()
        limit = self._clamp(limit, 1, 100)  # Files API allows up to 100
        cfg: Dict[str, Any] = {'page_size': limit}
        if after:
            cfg['page_token'] = after

        pager = client.files.list(config=cfg)
        for f in pager:
            name = getattr(f, "name", None)
            if name and name not in items:
                items.append(name)

        # The SDK pager auto-iterates pages; explicit tokens are optional
        return items

    def get_files_ids(self) -> List[str]:
        """
        Get Files API file names (single iterator over all pages)

        :return: list of file names
        """
        client = self.get_client()
        items = []
        pager = client.files.list()
        for f in pager:
            name = getattr(f, "name", None)
            if name and name not in items:
                items.append(name)
        return items

    def remove_files(self, callback: Optional[callable] = None) -> int:
        """
        Remove all Files API files

        :param callback: callback function
        :return: number of deleted files
        """
        num = 0
        files = self.get_files_ids()
        for file_name in files:
            self.log("Removing file: " + file_name, callback)
            try:
                res = self.delete_file(file_name)
                if res:
                    num += 1
            except Exception as e:
                msg = "Error removing file {}: {}".format(file_name, str(e))
                self.log(msg, callback)
        return num

    def remove_file(self, file_name: str, callback: Optional[callable] = None) -> bool:
        """
        Remove a single Files API file

        :param file_name: Files API resource name ('files/...').
        :param callback: callback function
        :return: True if removed
        """
        self.log("Removing file: " + file_name, callback)
        try:
            res = self.delete_file(file_name)
            return res is not None
        except Exception as e:
            msg = "Error removing file {}: {}".format(file_name, str(e))
            self.log(msg, callback)
            raise

    # -----------------------------
    # File Search stores
    # -----------------------------

    def import_stores(
            self,
            items: dict,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
            callback: Optional[callable] = None
    ) -> dict:
        """
        Import File Search stores

        :param items: items dict accumulator
        :param order: unused
        :param limit: page size (Google limit: 20)
        :param after: page token
        :param callback: callback
        :return: items dict of RemoteStoreItem
        """
        client = self.get_client()
        limit = self._clamp(limit, 1, 20)  # API limit = 20
        cfg: Dict[str, Any] = {'page_size': limit}
        if after:
            cfg['page_token'] = after

        pager = client.file_search_stores.list(config=cfg)
        for remote in pager:
            name = getattr(remote, "name", None)  # 'fileSearchStores/...'
            if not name:
                continue
            if name not in items:
                items[name] = RemoteStoreItem()
            items[name].id = name
            items[name].name = getattr(remote, "display_name", "") or ""
            items[name].file_ids = []
            items[name].provider = "google"

            status = self.window.core.remote_store.google.parse_status(remote)
            self.window.core.remote_store.google.append_status(items[name], status)
            self.log("Imported file search store: " + name, callback)

        return items

    def create_store(self, name: str, expire_days: int = 0):
        """
        Create File Search store

        :param name: display name
        :param expire_days: ignored (not supported)
        :return: store object
        """
        client = self.get_client()
        store = client.file_search_stores.create(config={'display_name': name})
        if store is not None:
            return store

    def update_store(self, id: str, name: str, expire_days: int = 0):
        """
        Update File Search store (no remote update available). Returns the current remote store.

        :param id: store name ('fileSearchStores/...').
        :param name: local alias (persisted locally)
        :param expire_days: ignored
        :return: store object (fresh get) or None if not found
        """
        try:
            return self.get_store(id)
        except Exception:
            return None

    def get_store(self, id: str):
        """
        Get File Search store

        :param id: store name ('fileSearchStores/...').
        :return: store object
        """
        client = self.get_client()
        return client.file_search_stores.get(name=id)

    def remove_store(self, id: str):
        """
        Delete File Search store (force delete related documents)

        :param id: store name ('fileSearchStores/...').
        :return: delete response
        """
        client = self.get_client()
        return client.file_search_stores.delete(name=id, config={'force': True})

    def get_stores_ids(
            self,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all File Search store names

        :param items: items accumulator
        :param order: unused
        :param limit: page size (Google limit 20)
        :param after: page token
        :return: list of store names
        """
        client = self.get_client()
        limit = self._clamp(limit, 1, 20)
        cfg: Dict[str, Any] = {'page_size': limit}
        if after:
            cfg['page_token'] = after

        pager = client.file_search_stores.list(config=cfg)
        for remote in pager:
            name = getattr(remote, "name", None)
            if name and name not in items:
                items.append(name)
        return items

    # -----------------------------
    # Documents within a store
    # -----------------------------

    def get_store_files_ids(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
    ) -> list:
        """
        Get all Document names for a File Search store

        :param store_id: store name ('fileSearchStores/...').
        :param items: items accumulator
        :param order: unused
        :param limit: page size (Google limit 20)
        :param after: page token
        :return: list of Document names ('fileSearchStores/.../documents/...').
        """
        client = self.get_client()
        limit = self._clamp(limit, 1, 20)
        cfg: Dict[str, Any] = {'page_size': limit}
        if after:
            cfg['page_token'] = after

        try:
            pager = client.file_search_stores.documents.list(parent=store_id, config=cfg)
        except Exception:
            pager = client.documents.list(parent=store_id, config=cfg)

        for remote in pager:
            name = getattr(remote, "name", None)
            if name and name not in items:
                items.append(name)
        return items

    def remove_from_stores(self) -> int:
        """
        Remove all documents from all File Search stores

        :return: number of deleted documents
        """
        stores = self.get_stores_ids([])
        num = 0
        for store_id in stores:
            files = self.get_store_files_ids(store_id, [])
            for doc_name in files:
                self.log("Removing document from store [{}]:{} ".format(store_id, doc_name))
                self.delete_store_file(store_id, doc_name)
                num += 1
        return num

    def remove_from_store(self, store_id: str) -> int:
        """
        Remove all documents from a specific File Search store

        :param store_id: store name ('fileSearchStores/...').
        :return: number of deleted documents
        """
        files = self.get_store_files_ids(store_id, [])
        num = 0
        for doc_name in files:
            self.log("Removing document from store [{}]:{} ".format(store_id, doc_name))
            self.delete_store_file(store_id, doc_name)
            num += 1
        return num

    def remove_all(self, callback: Optional[callable] = None) -> int:
        """
        Remove all File Search stores

        :param callback: callback function
        :return: number of deleted stores
        """
        num = 0
        stores = self.get_stores_ids([])
        for store_id in stores:
            self.log("Removing file search store: " + store_id, callback)
            try:
                self.remove_store(store_id)
                num += 1
            except Exception as e:
                msg = "Error removing file search store {}: {}".format(store_id, str(e))
                self.log(msg, callback)
        return num

    def add_file(self, store_id: str, file_name: str):
        """
        Import a Files API file into a File Search store.

        :param store_id: store name ('fileSearchStores/...').
        :param file_name: Files API file name ('files/...').
        :return: operation (long running)
        """
        client = self.get_client()
        op = client.file_search_stores.import_file(
            file_search_store_name=store_id,
            file_name=file_name,
        )
        return op

    def delete_store_file(self, store_id: str, document_name: str):
        """
        Delete a Document from a File Search store.

        :param store_id: store name ('fileSearchStores/...').
        :param document_name: document resource name ('fileSearchStores/.../documents/...').
        :return: delete response
        """
        client = self.get_client()
        return client.file_search_stores.documents.delete(name=document_name, config={'force': True})

    def remove_store_file(self, store_id: str, document_name: str):
        """
        Compatibility alias used by controller: remove a document from a File Search store.
        """
        return self.delete_store_file(store_id, document_name)

    def import_stores_files(self, callback: Optional[callable] = None) -> int:
        """
        Import all documents (files) from all File Search stores

        :param callback: callback function
        :return: number of imported documents
        """
        store_ids = self.get_stores_ids([])
        num = 0
        for store_id in store_ids:
            items = []
            try:
                items = self.import_store_files(store_id, items, callback=callback)
            except Exception as e:
                msg = "Error importing store {} documents list: {}".format(store_id, str(e))
                self.log(msg, callback)
            num += len(items)
        return num

    def import_store_files(
            self,
            store_id: str,
            items: list,
            order: str = "asc",
            limit: int = 100,
            after: Optional[str] = None,
            callback: Optional[callable] = None
    ) -> list:
        """
        Import a store's documents and insert into local DB

        :param store_id: store name ('fileSearchStores/...').
        :param items: accumulator
        :param order: unused
        :param limit: page size (Google limit 20)
        :param after: page token
        :param callback: log callback
        :return: list of imported document names
        """
        client = self.get_client()
        limit = self._clamp(limit, 1, 20)
        cfg: Dict[str, Any] = {'page_size': limit}
        if after:
            cfg['page_token'] = after

        try:
            pager = client.file_search_stores.documents.list(parent=store_id, config=cfg)
        except Exception:
            pager = client.documents.list(parent=store_id, config=cfg)

        for remote in pager:
            try:
                doc_name = getattr(remote, "name", None)
                if not doc_name:
                    continue
                if doc_name not in items:
                    items.append(doc_name)
                    try:
                        doc = client.file_search_stores.documents.get(name=doc_name)
                    except Exception:
                        doc = remote
                    self.window.core.remote_store.google.files.insert(store_id, doc)
                    msg = "Imported document {} to store {}".format(doc_name, store_id)
                    self.log(msg, callback)
            except Exception as e:
                msg = "Error importing document {} to store {}: {}".format(
                    getattr(remote, "name", "?"), store_id, str(e)
                )
                self.log(msg, callback)
        return items

    # -----------------------------
    # Convenience: direct upload to a store
    # -----------------------------

    def upload_to_store(self, store_id: str, path: str):
        """
        Directly upload a local file to a File Search store. This creates a Document.

        :param store_id: store name ('fileSearchStores/...').
        :param path: file path
        :return: created document object or None
        """
        client = self.get_client()
        if not os.path.exists(path):
            return None

        basename = os.path.basename(path)
        op = client.file_search_stores.upload_to_file_search_store(
            file=path,
            file_search_store_name=store_id,
            config={'display_name': basename},
        )

        for _ in range(180):
            if getattr(op, "done", False):
                break
            time.sleep(2)
            op = client.operations.get(op)

        try:
            docs = self.get_store_files_ids(store_id, [])
            for doc_name in docs:
                try:
                    d = client.file_search_stores.documents.get(name=doc_name)
                except Exception:
                    continue
                if getattr(d, "display_name", None) == basename:
                    return d
        except Exception:
            pass

        return None