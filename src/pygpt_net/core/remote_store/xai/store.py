#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 06:00:00                  #
# ================================================== #

import datetime
from typing import Optional, List, Dict, Any

from packaging.version import Version

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.provider.core.remote_store.db_sqlite import DbSqliteProvider

from .files import Files


class Store:
    """
    xAI Collections API store adapter.

    Each xAI Collection is mapped to a RemoteStoreItem (Vector Store analogue).
    """

    PROVIDER_NAME = "xai"

    def __init__(self, window=None):
        """
        xAI Collections core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.files = Files(window)
        self.items: Dict[str, RemoteStoreItem] = {}

    def install(self):
        """Install provider data"""
        self.provider.install()
        self.files.install()

    def patch(self, app_version: Version) -> bool:
        """Patch provider data"""
        res1 = self.files.patch(app_version)
        res2 = self.provider.patch(app_version)
        return res1 or res2

    def get(self, id: str) -> RemoteStoreItem:
        if id in self.items:
            return self.items[id]

    def get_ids(self) -> List[str]:
        return list(self.items.keys())

    def get_all(self) -> Dict[str, RemoteStoreItem]:
        return self.items

    def get_id_by_idx_all(self, idx: int) -> str:
        return list(self.items.keys())[idx]

    def get_by_idx(self, idx: int) -> str:
        items = self.items
        return list(items.keys())[idx]

    def has(self, id: str) -> bool:
        return id in self.items

    # ---------- CRUD ----------

    def create(self, name: Optional[str] = None) -> Optional[RemoteStoreItem]:
        """
        Create a new collection.
        """
        name = name or "New collection"
        collection = self.window.core.api.xai.store.create_collection_collections(name)
        if collection is None:
            return None
        store = RemoteStoreItem()
        store.id = getattr(collection, "collection_id", None)
        store.name = getattr(collection, "collection_name", None) or name
        store.provider = self.PROVIDER_NAME
        store.is_thread = False
        store.record_id = self.provider.create(store)
        self.items[store.id] = store
        return store

    def update(self, store: RemoteStoreItem) -> Optional[RemoteStoreItem]:
        """
        Update collection (rename).
        """
        collection = self.window.core.api.xai.store.update_collection_collections(store.id, store.name)
        if collection is None:
            return None
        self.items[store.id] = store
        self.provider.save(store)
        return store

    def get_status_data(self, id: str):
        """
        Obtain status data for a collection.
        """
        status = {}
        data = self.window.core.api.xai.store.get_collection_collections(id)
        if data is not None:
            stats = self.window.core.api.xai.store.get_collection_stats_collections(id)
            status = {
                "status": "ready",
                "usage_bytes": int(stats.get("total_bytes", 0) or 0),
                "expires_at": None,
                "last_active_at": int(datetime.datetime.now().timestamp()),
                "file_counts": {
                    "in_progress": 0,
                    "completed": int(stats.get("count", 0) or 0),
                    "cancelled": 0,
                    "failed": 0,
                    "total": int(stats.get("count", 0) or 0),
                },
                "expires_after": None,
                "remote_display_name": getattr(data, "name", "") or "",
            }
        return status, data

    def update_status(self, id: str):
        """
        Refresh store status from remote collection.
        """
        if id not in self.items:
            return
        store = self.items[id]
        status, data = self.get_status_data(id)
        if data is not None:
            tmp_name = getattr(data, "collection_name", None) or ""
            store.name = tmp_name
        store.provider = self.PROVIDER_NAME
        self.append_status(store, status)
        self.update(store)

    def append_status(self, store: RemoteStoreItem, status: Dict[str, Any]):
        import datetime as _dt
        now = _dt.datetime.now()
        ts = int(now.timestamp())
        status["__last_refresh__"] = now.strftime("%Y-%m-%d %H:%M:%S")
        store.status = status
        store.last_sync = ts
        if "status" in status:
            store.last_status = status["status"]
        if "usage_bytes" in status:
            store.usage_bytes = status["usage_bytes"]
        if "file_counts" in status:
            store.num_files = status["file_counts"]["total"]
        if "last_active_at" in status and status["last_active_at"]:
            store.last_active = int(status["last_active_at"])

    def get_names(self) -> Dict[str, str]:
        names = {}
        for id in self.items:
            store = self.items[id]
            names[id] = store.name
        return names

    def delete(self, id: str) -> bool:
        """
        Delete collection.
        """
        if id in self.items:
            store = self.items[id]
            self.provider.delete_by_id(store.record_id)
            try:
                self.window.core.api.xai.store.remove_collection_collections(id)
            except Exception as e:
                self.window.core.debug.log(e)
            del self.items[id]
            return True
        return False

    def import_items(self, items: Dict[str, RemoteStoreItem]):
        """
        Insert items (collections).
        """
        self.items = items
        for item in items.values():
            item.provider = self.PROVIDER_NAME
            item.record_id = self.provider.create(item)

    def clear(self):
        self.truncate()

    def is_hidden(self, id: str) -> bool:
        return False

    def truncate(self) -> bool:
        self.provider.truncate(self.PROVIDER_NAME)
        self.items = {}
        return True

    # ---------- Load/Save ----------

    def load(self):
        self.items = self.provider.load_all(self.PROVIDER_NAME)
        self.sort_items()

    def load_all(self):
        self.load()
        self.files.load()

    def sort_items(self):
        pass

    def save(self):
        self.provider.save_all(self.items)

    def get_version(self) -> str:
        return self.provider.get_version()