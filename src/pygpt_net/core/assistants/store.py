#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import datetime
from typing import Optional, List, Dict, Any

from packaging.version import Version

from pygpt_net.item.assistant import AssistantStoreItem, AssistantItem
from pygpt_net.provider.core.assistant_store.db_sqlite import DbSqliteProvider


class Store:
    def __init__(self, window=None):
        """
        Assistant vector store core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.items = {}

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def get(self, id: str) -> AssistantStoreItem:
        """
        Get store item by store_id

        :param id: store ID
        :return: store item
        """
        if id in self.items:
            return self.items[id]

    def get_ids(self) -> List[str]:
        """
        Return all loaded store IDs

        :return: store ids list
        """
        return list(self.items.keys())


    def get_all(self) -> Dict[str, AssistantStoreItem]:
        """
        Return all stores

        :return: all stores
        """
        return self.items

    def get_id_by_idx_all(self, idx: int) -> str:
        """
        Return store id by index

        :param idx: store idx
        :return: store id
        """
        return list(self.items.keys())[idx]


    def get_by_idx(self, idx: int) -> str:
        """
        Return store by index

        :param idx: store idx
        :return: model name
        """
        items = self.items
        return list(items.keys())[idx]


    def has(self, id: str) -> bool:
        """
        Check if store exists

        :param id: store id
        :return: True if store exists
        """
        return id in self.items

    def create(self) -> Optional[AssistantStoreItem]:
        """
        Create new store

        :return: store item
        """
        name = "New vector store"
        vector_store = self.window.core.gpt.store.create_store(name, 0)
        if vector_store is None:
            return None
        store = AssistantStoreItem()
        store.id = vector_store.id
        store.name = name
        store.is_thread = False
        store.record_id = self.provider.create(store)
        self.items[store.id] = store
        return store

    def update(self, store: AssistantStoreItem) -> Optional[AssistantStoreItem]:
        """
        Update store

        :param store: store
        :return: updated store or None if failed
        """
        vector_store = self.window.core.gpt.store.update_store(store.id, store.name, store.expire_days)
        if vector_store is None:
            return None
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
        data = self.window.core.gpt.store.get_store(id)
        if data is not None:
            status = self.parse_status(data)
        return status, data

    def parse_status(self, store) -> Dict[str, Any]:
        """
        Parse store status

        :param store: store API object
        :return: status dict
        """
        status = {
            "status": store.status,
            "usage_bytes": store.usage_bytes,
            "expires_at": store.expires_at,
            "last_active_at": store.last_active_at,
        }
        if store.file_counts:
            status["file_counts"] = {
                "in_progress": store.file_counts.in_progress,
                "completed": store.file_counts.completed,
                "cancelled": store.file_counts.cancelled,
                "failed": store.file_counts.failed,
                "total": store.file_counts.total,
            }
        if store.expires_after:
            status["expires_after"] = {
                "anchor": store.expires_after.anchor,
                "days": store.expires_after.days,
            }
        return status

    def update_status(self, id: str):
        """
        Update store status

        :param id: store id
        """
        store = self.items[id]
        status, data = self.get_status_data(id)  # get from API
        tmp_name = data.name
        if tmp_name is None:
            tmp_name = ""
        store.name = tmp_name
        self.append_status(store, status)  # append to store
        self.update(store)  # save to db

    def append_status(
            self,
            store: AssistantStoreItem,
            status: Dict[str, Any]
    ):
        """
        Append status to store

        :param store: store
        :param status: status
        """
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
        if "last_active_at" in status:
            store.last_active = int(status["last_active_at"])
        if "expires_after" in status:
            store.expire_days = int(status["expires_after"]["days"] or 0)

    def get_names(self) -> Dict[str, str]:
        """
        Get store name mapping id <> name

        :return: store names
        """
        names = {}
        for id in self.items:
            store = self.items[id]
            names[id] = store.name
        return names

    def delete(self, id: str) -> bool:
        """
        Delete store

        :param id: store id
        :return: True if store was deleted
        """
        if id in self.items:
            store = self.items[id]
            self.provider.delete_by_id(store.record_id)
            self.window.core.gpt.store.remove_store(id)
            del self.items[id]
            return True
        return False

    def import_items(self, items: Dict[str, AssistantStoreItem]):
        """
        Insert items

        :param items: items
        """
        self.items = items
        for item in items.values():
            item.record_id = self.provider.create(item)

    def clear(self):
        """Clear all stores"""
        self.truncate()

    def is_hidden(self, id: str) -> bool:
        """
        Check if store is hidden

        :param id: store id
        :return: True if store is hidden
        """
        if id in self.items:
            if (self.window.core.config.get("assistant.store.hide_threads")
                    and (self.items[id].name is None or self.items[id].name == "")):
                return True
        return False

    def truncate(self) -> bool:
        """
        Truncate all stores

        :return: True if truncated
        """
        self.provider.truncate()
        self.items = {}
        return True

    def load(self):
        """Load store"""
        self.items = self.provider.load_all()
        self.sort_items()

    def sort_items(self):
        """Sort items"""
        pass

    def save(self):
        """Save store"""
        self.provider.save_all(self.items)

    def get_version(self) -> str:
        """
        Get config version

        :return: version
        """
        return self.provider.get_version()
