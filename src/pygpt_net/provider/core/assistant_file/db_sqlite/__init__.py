#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 16:00:00                  #
# ================================================== #

import uuid

from packaging.version import Version

from pygpt_net.item.assistant import AssistantFileItem
from pygpt_net.provider.core.assistant_file.base import BaseProvider

from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "assistant_file"

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

    def create(self, file: AssistantFileItem) -> int:
        """
        Create new and return its ID

        :param file: AssistantFileItem
        :return: file ID
        """
        if file.record_id is None or file.record_id == "":
            file.uuid = self.create_id()
            file.record_id = self.storage.insert(file)
        return file.record_id

    def load_all(self) -> dict:
        """
        Load files from DB

        :return: files dict
        """
        return self.storage.get_all()

    def load(self, id: int) -> AssistantFileItem:
        """
        Load file from DB

        :param id: file ID
        :return: file item
        """
        return self.storage.get_by_id(id)

    def save(self, file: AssistantFileItem):
        """
        Save file to DB

        :param file: AssistantFileItem
        """
        try:
            self.storage.save(file)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving filed: {}".format(str(e)))

    def save_all(self, items: dict):
        """
        Save all files to DB

        :param items: dict of AssistantFileItem objects
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
        Return dict with AssistantFileItem objects, indexed by record ID

        :return: dict of AssistantFileItem objects
        """
        return self.storage.get_by_store_or_thread(store_id, thread_id)

    def count_by_store_or_thread(self, store_id: str, thread_id: str) -> int:
        """
        Count AssistantFileItem objects, indexed by ID

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

    def clear_all_stores_from_files(self) -> bool:
        """
        Clear all stores from files

        :return: True if deleted
        """
        return self.storage.clear_all_stores_from_files()

    def rename_file(self, record_id: int, name: str) -> bool:
        """
        Rename file

        :param record_id: record ID
        :param name: new name
        :return: True if renamed
        """
        return self.storage.rename_file(record_id, name)

    def truncate_all(self) -> bool:
        """
        Truncate all files

        :return: True if truncated
        """
        return self.storage.truncate_all()

    def truncate_by_store(self, store_id: str) -> bool:
        """
        Truncate all files

        :param store_id: store ID
        :return: True if truncated
        """
        return self.storage.truncate_by_store(store_id)


