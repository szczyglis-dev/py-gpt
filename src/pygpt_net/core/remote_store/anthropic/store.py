#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 17:00:00                  #
# ================================================== #

import datetime
from typing import Optional, List, Dict, Any

from packaging.version import Version

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.provider.core.remote_store.db_sqlite import DbSqliteProvider

from .files import Files


class Store:
    """
    Anthropic Files API "store" adapter.
    Anthropic does not have vector stores; we expose a single workspace-level pseudo store.
    """

    PROVIDER_NAME = "anthropic"
    DEFAULT_STORE_ID = "files"
    DEFAULT_STORE_NAME = "Files"

    def __init__(self, window=None):
        """
        Anthropic Files workspace core

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

    def _ensure_default(self) -> RemoteStoreItem:
        """Ensure default pseudo-store exists locally."""
        if self.DEFAULT_STORE_ID in self.items:
            return self.items[self.DEFAULT_STORE_ID]
        store = RemoteStoreItem()
        store.id = self.DEFAULT_STORE_ID
        store.name = self.DEFAULT_STORE_NAME
        store.provider = self.PROVIDER_NAME
        store.is_thread = False
        store.record_id = self.provider.create(store)
        self.items[store.id] = store
        return store

    def create(self, name: Optional[str] = None) -> Optional[RemoteStoreItem]:
        """
        Create workspace-level pseudo-store (idempotent).

        :param name: local alias
        :return: store item
        """
        store = self._ensure_default()
        if name:
            store.name = name
            self.provider.save(store)
        return store

    def update(self, store: RemoteStoreItem) -> Optional[RemoteStoreItem]:
        """
        Update local store metadata (no remote update).
        """
        self.items[store.id] = store
        self.provider.save(store)
        return store

    def get_status_data(self, id: str):
        """
        Compute workspace status from Files API
        """
        status = {}
        stats = self.window.core.api.anthropic.store.get_files_stats()
        if stats is not None:
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
                "remote_display_name": self.items.get(id, RemoteStoreItem()).name if id in self.items else self.DEFAULT_STORE_NAME,
            }
        return status, None

    def update_status(self, id: str):
        """
        Update pseudo-store status
        """
        self._ensure_default()
        store = self.items[id]
        status, _ = self.get_status_data(id)
        self.append_status(store, status)
        self.update(store)

    def append_status(self, store: RemoteStoreItem, status: Dict[str, Any]):
        now = datetime.datetime.now()
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
        if id in self.items:
            store = self.items[id]
            self.provider.delete_by_id(store.record_id)
            del self.items[id]
            return True
        return False

    def import_items(self, items: Dict[str, RemoteStoreItem]):
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

    def load(self):
        self.items = self.provider.load_all(self.PROVIDER_NAME)
        if self.DEFAULT_STORE_ID not in self.items:
            # Ensure default exists
            self._ensure_default()
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