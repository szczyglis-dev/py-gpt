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

import uuid
from typing import Dict

from packaging.version import Version

from pygpt_net.item.store import RemoteFileItem
from pygpt_net.provider.core.remote_file.base import BaseProvider

from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "remote_file"

    def attach(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window
        self.storage.attach(window)

    def patch(self, version: Version) -> bool:
        """
        Patch versions

        :param version: current app version
        :return: True if migrated
        """
        return self.patcher.execute(version)

    def create_id(self) -> str:
        """
        Create unique uuid

        :return: uuid
        """
        return str(uuid.uuid4())

    def create(self, file: RemoteFileItem) -> int:
        """
        Create new and return its ID

        :param file: RemoteFileItem
        :return: file ID
        """
        if file.record_id is None or file.record_id == "":
            file.uuid = self.create_id()
            file.record_id = self.storage.insert(file)
        return file.record_id

    def load_all(self, provider: str) -> Dict[str, RemoteFileItem]:
        """
        Load files from DB

        :param provider: provider ID
        :return: files dict
        """
        return self.storage.get_all(provider)

    def load(self, id: int) -> RemoteFileItem:
        """
        Load file from DB

        :param id: file ID
        :return: file item
        """
        return self.storage.get_by_id(id)

    def save(self, file: RemoteFileItem):
        """
        Save file to DB

        :param file: RemoteFileItem
        """
        try:
            self.storage.save(file)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving filed: {}".format(str(e)))

    def save_all(self, items: Dict[str, RemoteFileItem]):
        """
        Save all files to DB

        :param items: dict of RemoteFileItem objects
        """
        try:
            for id in items:
                file = items[id]
                self.storage.save(file)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving file: {}".format(str(e)))

    def get_by_store_or_thread(self, store_id: str, thread_id: str) -> dict:
        """
        Return dict with RemoteFileItem objects, indexed by record ID

        :return: dict of RemoteFileItem objects
        """
        return self.storage.get_by_store_or_thread(store_id, thread_id)

    def count_by_store_or_thread(self, store_id: str, thread_id: str) -> int:
        """
        Count RemoteFileItem objects, indexed by ID

        :return: number of files
        """
        return self.storage.count_by_store_or_thread(store_id, thread_id)

    def get_all_by_file_id(self, file_id: str) -> dict:
        """
        Get all files by file ID

        :param file_id: file ID
        :return: files dict
        """
        return self.storage.get_all_by_file_id(file_id)

    def delete_by_id(self, id: int) -> bool:
        """
        Delete file by ID

        :param id: file ID
        :return: True if deleted
        """
        return self.storage.delete_by_id(id)

    def delete_by_file_id(self, file_id: str) -> bool:
        """
        Delete file by file ID

        :param file_id: file ID
        :return: True if deleted
        """
        return self.storage.delete_by_file_id(file_id)

    def clear_store_from_files(self, store_id: str) -> bool:
        """
        Clear store from files

        :param store_id: store ID
        :return: True if deleted
        """
        return self.storage.clear_store_from_files(store_id)

    def clear_all_stores_from_files(self, provider: str) -> bool:
        """
        Clear all stores from files

        :param provider: provider ID
        :return: True if deleted
        """
        return self.storage.clear_all_stores_from_files(provider)

    def rename_file(self, record_id: int, name: str) -> bool:
        """
        Rename file

        :param record_id: record ID
        :param name: new name
        :return: True if renamed
        """
        return self.storage.rename_file(record_id, name)

    def truncate_all(self, provider: str) -> bool:
        """
        Truncate all files

        :param provider: provider ID
        :return: True if truncated
        """
        return self.storage.truncate_all(provider)

    def truncate_by_store(self, store_id: str) -> bool:
        """
        Truncate all files

        :param store_id: store ID
        :return: True if truncated
        """
        return self.storage.truncate_by_store(store_id)


