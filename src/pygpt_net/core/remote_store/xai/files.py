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

from typing import Optional, List, Dict, Union

from packaging.version import Version

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.store import RemoteFileItem
from pygpt_net.provider.core.remote_file.db_sqlite import DbSqliteProvider


class Files:

    PROVIDER_NAME = "xai"
    DEFAULT_STORE_ID = "files"

    def __init__(self, window=None):
        """
        xAI remote files core (workspace Files API)

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.items: Dict[str, RemoteFileItem] = {}

    def install(self):
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        return self.provider.patch(app_version)

    def get(self, id: str) -> Optional[RemoteFileItem]:
        if id in self.items:
            return self.items[id]
        return None

    def get_ids(self) -> List[str]:
        return list(self.items.keys())

    def get_all(self) -> Dict[str, RemoteFileItem]:
        return self.items

    def get_id_by_idx_all(self, idx: int) -> str:
        return list(self.items.keys())[idx]

    def get_by_idx(self, idx: int) -> str:
        items = self.items
        return list(items.keys())[idx]

    def has(self, id: str) -> bool:
        return id in self.items

    def create(
            self,
            assistant: AssistantItem,
            thread_id: str,
            file_id: str,
            name: str,
            path: str,
            size: int) -> Optional[RemoteFileItem]:
        """
        Not used in the xAI path (kept for parity).
        """
        file = RemoteFileItem()
        file.id = file_id
        file.file_id = file_id
        file.thread_id = thread_id or ""
        file.provider = self.PROVIDER_NAME
        file.name = name
        file.path = path
        file.size = size or 0
        file.store_id = self.DEFAULT_STORE_ID
        file.record_id = self.provider.create(file)
        self.items[file.id] = file
        return file

    def update(self, file: RemoteFileItem) -> Optional[RemoteFileItem]:
        self.items[file.id] = file
        self.provider.save(file)
        return file

    def get_names(self) -> Dict[str, str]:
        names = {}
        for id in self.items:
            file = self.items[id]
            names[id] = file.name
        return names

    def get_by_store_or_thread(self, store_id: str, thread_id: str) -> Dict[str, RemoteFileItem]:
        return self.provider.get_by_store_or_thread(store_id, thread_id)

    def count_by_store_or_thread(self, store_id: str, thread_id: str) -> int:
        return self.provider.count_by_store_or_thread(store_id, thread_id)

    def get_file_by_idx(self, idx: int, store_id: str, thread_id: str) -> Optional[RemoteFileItem]:
        files = self.get_by_store_or_thread(store_id, thread_id)
        if idx >= len(files):
            return None
        return list(files.values())[idx]

    def get_file_id_by_idx(self, idx: int, store_id: str, thread_id: str) -> Optional[str]:
        file = self.get_file_by_idx(idx, store_id, thread_id)
        if file is None:
            return None
        return file.file_id

    def get_all_by_file_id(self, file_id: str) -> dict:
        return self.provider.get_all_by_file_id(file_id)

    def delete(self, file: Union[RemoteFileItem, list]) -> bool:
        files = file if isinstance(file, list) else [file]
        for f in files:
            file_id = f.file_id
            try:
                self.window.core.api.xai.store.remove_file(file_id)
            except Exception as e:
                self.window.core.debug.log("Failed to delete remote file: " + str(e))
            self.provider.delete_by_id(f.record_id)
            if f.record_id in self.items:
                del self.items[f.record_id]
        return True

    def delete_by_file_id(self, file_id: str) -> bool:
        res = self.provider.delete_by_file_id(file_id)
        if res:
            to_delete = []
            for id in self.items:
                if self.items[id].file_id == file_id:
                    to_delete.append(id)
            for id in to_delete:
                del self.items[id]
        return res

    def on_store_deleted(self, store_id: str):
        self.provider.clear_store_from_files(store_id)

    def on_all_stores_deleted(self):
        self.provider.clear_all_stores_from_files(self.PROVIDER_NAME)

    def rename(self, record_id: int, name: str) -> bool:
        self.provider.rename_file(record_id, name)
        if record_id in self.items:
            self.items[record_id].name = name
        return True

    def truncate(self, store_id: Optional[str] = None) -> bool:
        self.window.core.api.xai.store.remove_files()
        return self.truncate_local(store_id)

    def truncate_local(self, store_id: Optional[str] = None) -> bool:
        if store_id is not None:
            self.provider.truncate_by_store(store_id)
        else:
            self.provider.truncate_all(self.PROVIDER_NAME)
            self.items = {}
        return True

    def import_from_store(self, store_id: str) -> bool:
        files = self.window.core.api.xai.store.import_files()
        for f in files:
            pass
        return True

    def insert(self, store_id: str, data) -> RemoteFileItem:
        """
        Insert a File into local DB

        :param store_id: pseudo store id ('files')
        :param data: file object from API
        """
        file = RemoteFileItem()
        file.id = getattr(data, "id", None) or getattr(data, "name", None)
        file.file_id = getattr(data, "id", None) or getattr(data, "name", None)
        file.thread_id = ""
        file.name = getattr(data, "filename", None) or getattr(data, "name", "") or file.file_id
        file.provider = self.PROVIDER_NAME
        file.path = file.name
        try:
            size = getattr(data, "size_bytes", None)
            if size is None and hasattr(data, "size"):
                size = getattr(data, "size")
            file.size = int(size or 0)
        except Exception:
            file.size = 0
        file.store_id = self.DEFAULT_STORE_ID
        file.record_id = self.provider.create(file)
        self.items[file.id] = file
        return file

    def load(self):
        self.items = self.provider.load_all(self.PROVIDER_NAME)
        self.sort_items()

    def sort_items(self):
        return

    def save(self):
        self.provider.save_all(self.items)

    def get_version(self) -> str:
        return self.provider.get_version()