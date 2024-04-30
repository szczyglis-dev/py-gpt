#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 04:00:00                  #
# ================================================== #

from packaging.version import Version

from pygpt_net.item.assistant import AssistantFileItem, AssistantItem
from pygpt_net.provider.core.assistant_file.db_sqlite import DbSqliteProvider


class Files:
    def __init__(self, window=None):
        """
        Assistant files core

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

    def get(self, id: str) -> AssistantFileItem:
        """
        Get file item by file_id

        :param id: file ID
        :return: file item
        """
        if id in self.items:
            return self.items[id]

    def get_ids(self) -> list:
        """
        Return all loaded file IDs

        :return: file ids list
        """
        return list(self.items.keys())


    def get_all(self) -> dict:
        """
        Return all files

        :return: all files
        """
        return self.items

    def get_id_by_idx_all(self, idx: int) -> str:
        """
        Return file id by index

        :param idx: file idx
        :return: file id
        """
        return list(self.items.keys())[idx]


    def get_by_idx(self, idx: int) -> str:
        """
        Return file by index

        :param idx: file idx
        :return: model name
        """
        items = self.items
        return list(items.keys())[idx]


    def has(self, id: str) -> bool:
        """
        Check if file exists

        :param id: file id
        :return: True if file exists
        """
        return id in self.items

    def create(
            self,
            assistant: AssistantItem,
            thread_id: str,
            file_id: str,
            name: str,
            path: str,
            size: int) -> AssistantFileItem or None:
        """
        Create new file

        :param assistant: assistant item
        :param thread_id: thread ID
        :param file_id: file ID
        :param name: file name
        :param path: file path
        :param size: file size
        :return: file item
        """
        file = AssistantFileItem()
        file.id = file_id
        file.file_id = file_id
        file.thread_id = thread_id
        file.name = name
        file.path = path
        file.size = size
        if assistant.vector_store is not None and assistant.vector_store != "":
            file.store_id = assistant.vector_store
        file.record_id = self.provider.create(file)
        self.items[file.id] = file
        return file

    def update(self, file: AssistantFileItem) -> AssistantFileItem or None:
        """
        Update file

        :param file: file
        :return: updated file or None if failed
        """
        self.items[file.id] = file
        self.provider.save(file)
        return file

    def get_names(self) -> dict:
        """
        Get file name mapping id <> name

        :return: file names
        """
        names = {}
        for id in self.items:
            file = self.items[id]
            names[id] = file.name
        return names

    def get_by_store_or_thread(self, store_id: str, thread_id: str) -> dict:
        """
        Get files by store or thread

        :param store_id: store ID
        :param thread_id: thread ID
        :return: files dict
        """
        return self.provider.get_by_store_or_thread(store_id, thread_id)

    def count_by_store_or_thread(self, store_id: str, thread_id: str) -> int:
        """
        Count files by store or thread

        :param store_id: store ID
        :param thread_id: thread ID
        :return: files dict
        """
        return self.provider.count_by_store_or_thread(store_id, thread_id)

    def get_file_by_idx(self, idx: int, store_id: str, thread_id: str) -> AssistantFileItem or None:
        """
        Get file by list index

        :param idx: file index
        :param store_id: store ID
        :param thread_id: thread ID
        :return: file item
        """
        files = self.get_by_store_or_thread(store_id, thread_id)
        if idx >= len(files):
            return None
        return list(files.values())[idx]

    def get_file_id_by_idx(self, idx: int, store_id: str, thread_id: str) -> str or None:
        """
        Get file by list index

        :param idx: file index
        :param store_id: store ID
        :param thread_id: thread ID
        :return: file item
        """
        file = self.get_file_by_idx(idx, store_id, thread_id)
        if file is None:
            return None
        return file.file_id

    def get_all_by_file_id(self, file_id: str) -> dict:
        """
        Get all files by file ID

        :param file_id: file ID
        :return: files dict
        """
        return self.provider.get_all_by_file_id(file_id)

    def delete(self, file: AssistantFileItem) -> bool:
        """
        Delete file and remove from vector stores if exists

        :param file: file item
        :return: True if file was deleted
        """
        file_id = file.file_id
        items = self.get_all_by_file_id(file_id)  # get store_ids
        for id in items:
            store_id = items[id].store_id
            if store_id is None or store_id == "":
                continue  # skip if no store_id
            try:
                self.window.core.gpt.store.delete_store_file(store_id, file_id)  # remove from vector store
            except Exception as e:
                self.window.core.debug.log("Failed to delete file from vector store: " + str(e))
        self.provider.delete_by_id(file.record_id)  # delete file in DB
        try:
            self.window.core.gpt.store.delete_file(file.file_id)  # delete file in API
        except Exception as e:
            self.window.core.debug.log("Failed to delete remote file: " + str(e))
        if file.record_id in self.items:
            del self.items[file.record_id]
        return True

    def on_store_deleted(self, store_id: str):
        """
        Clear deleted store from files

        :param store_id: store ID
        """
        self.provider.clear_store_from_files(store_id)

    def on_all_stores_deleted(self):
        """Clear all deleted stores from files"""
        self.provider.clear_all_stores_from_files()

    def rename(self, record_id: int, name: str) -> bool:
        """
        Rename file

        :param record_id: record ID
        :param name: new name
        :return: True if renamed
        """
        self.provider.rename_file(record_id, name)
        if record_id in self.items:
            self.items[record_id].name = name
        return True

    def truncate(self, store_id: str = None) -> bool:
        """
        Truncate all files

        :param store_id: store ID
        :return: True if truncated
        """
        if store_id is not None:
            self.window.core.gpt.store.remove_from_store(store_id)  # remove files from vector store
        else:
            self.window.core.gpt.store.remove_from_stores()  # remove files from all vector stores
        return self.truncate_local(store_id)  # truncate files in DB

    def truncate_local(self, store_id: str = None) -> bool:
        """
        Truncate all files (local only)

        :param store_id: store ID
        :return: True if truncated
        """
        if store_id is not None:
            self.provider.truncate_by_store(store_id)  # truncate files in DB (by store_id)
        else:
            self.provider.truncate_all()  # truncate all files in DB
            self.items = {}  # clear items
        return True

    def import_from_store(self, store_id: str) -> bool:
        """
        Import files from store

        :param store_id: store ID
        :return: True if imported
        """
        files = self.window.core.gpt.store.import_store_files(store_id)
        for file in files:
            self.create(file.assistant, file.thread_id, file.file_id, file.name, file.path, file.size)
        return True

    def insert(self, store_id: str, data) -> AssistantFileItem:
        """
        Insert file object

        :param store_id: store ID
        :param data: file data from API
        """
        file = AssistantFileItem()
        file.id = data.id
        file.file_id = data.id
        file.thread_id = ""
        file.name = data.filename
        file.path = data.filename
        file.size = data.bytes
        file.store_id = store_id
        file.record_id = self.provider.create(file)
        self.items[file.id] = file
        return file

    def load(self):
        """Load file"""
        self.items = self.provider.load_all()
        self.sort_items()

    def sort_items(self):
        """Sort items"""
        return
        self.items = dict(sorted(self.items.items(), key=lambda item: item[0]))

    def save(self):
        """Save file"""
        self.provider.save_all(self.items)

    def get_version(self) -> str:
        """Get config version"""
        return self.provider.get_version()
