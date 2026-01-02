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

import datetime
from typing import Optional, List, Dict, Any

from packaging.version import Version

from pygpt_net.item.store import RemoteStoreItem
from pygpt_net.provider.core.remote_store.db_sqlite import DbSqliteProvider

from .files import Files


class Store:

    PROVIDER_NAME = "google"

    def __init__(self, window=None):
        """
        Google File Search store core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.files = Files(window)
        self.items = {}

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

    def create(self, name: Optional[str] = None) -> Optional[RemoteStoreItem]:
        """
        Create new File Search store

        :param name: display name for the store (also used as local alias)
        :return: store item
        """
        # Use provided name or fallback
        display_name = name or "New file search store"

        # Create remote store with a display name
        vector_store = self.window.core.api.google.store.create_store(display_name, 0)
        if vector_store is None:
            return None

        # Build local item; set local alias to the provided name
        store = RemoteStoreItem()
        store.id = getattr(vector_store, "name", None)  # 'fileSearchStores/...'
        # Keep local alias as the passed name; fallback to remote display_name if missing
        store.name = display_name or (getattr(vector_store, "display_name", None) or "")
        store.provider = self.PROVIDER_NAME
        store.is_thread = False
        store.record_id = self.provider.create(store)
        self.items[store.id] = store
        return store

    def update(self, store: RemoteStoreItem) -> Optional[RemoteStoreItem]:
        """
        Update store (local persist; remote update is not supported by Google)
        """
        vector_store = self.window.core.api.google.store.update_store(store.id, store.name, store.expire_days)
        # Always persist local metadata (alias)
        self.items[store.id] = store
        self.provider.save(store)
        return store

    def get_status_data(self, id: str):
        """
        Get store status data

        :param id: store id
        :return: status data, store data
        """
        status = {}
        data = self.window.core.api.google.store.get_store(id)
        if data is not None:
            status = self.parse_status(data)
        return status, data

    def parse_status(self, store) -> Dict[str, Any]:
        """
        Map Google File Search store status to local fields
        """
        def _to_int(x):
            try:
                return int(x or 0)
            except Exception:
                return 0

        active = _to_int(getattr(store, "active_documents_count", 0))
        pending = _to_int(getattr(store, "pending_documents_count", 0))
        failed = _to_int(getattr(store, "failed_documents_count", 0))
        size_bytes = _to_int(getattr(store, "size_bytes", 0))
        update_time = getattr(store, "update_time", None)
        display_name = getattr(store, "display_name", None) or ""

        status_str = "ready"
        if pending > 0:
            status_str = "indexing"
        if failed > 0 and active == 0 and pending == 0:
            status_str = "failed"

        status = {
            "status": status_str,
            "usage_bytes": size_bytes,
            "expires_at": None,
            "last_active_at": self._parse_rfc3339_to_epoch(update_time) if update_time else None,
            "file_counts": {
                "in_progress": pending,
                "completed": active,
                "cancelled": 0,
                "failed": failed,
                "total": active + pending + failed,
            },
            "expires_after": None,
            "remote_display_name": display_name,
        }
        return status

    def _parse_rfc3339_to_epoch(self, s: str) -> int:
        """Convert RFC3339 to epoch seconds if possible"""
        try:
            s2 = s.replace('Z', '+00:00')
            ts = datetime.datetime.fromisoformat(s2)
            return int(ts.timestamp())
        except Exception:
            return int(datetime.datetime.now().timestamp())

    def update_status(self, id: str):
        """
        Update store status and keep local alias if set
        """
        store = self.items[id]
        status, data = self.get_status_data(id)
        remote_name = getattr(data, "display_name", None) if data else None
        # Keep local alias if user set it; otherwise adopt remote display name
        if not store.name or store.name.strip() == "":
            store.name = remote_name or ""
        store.provider = self.PROVIDER_NAME
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
            self.window.core.api.google.store.remove_store(id)
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
        if id in self.items:
            if (self.window.core.config.get("remote_store.google.hide_threads")
                    and (self.items[id].name is None or self.items[id].name == "")):
                return True
        return False

    def truncate(self) -> bool:
        self.provider.truncate(self.PROVIDER_NAME)
        self.items = {}
        return True

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