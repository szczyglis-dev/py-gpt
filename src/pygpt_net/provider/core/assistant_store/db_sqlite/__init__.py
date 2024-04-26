#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This store is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

import uuid

from packaging.version import Version

from pygpt_net.item.assistant import AssistantStoreItem
from pygpt_net.provider.core.assistant_store.base import BaseProvider

from .patch import Patch
from .storage import Storage


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "assistant_store"

    def attach(self, window):
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

    def create(self, store: AssistantStoreItem) -> int:
        """
        Create new and return its ID

        :param store: AssistantStoreItem
        :return: store ID
        """
        if store.record_id is None or store.record_id == "":
            store.uuid = self.create_id()
            store.record_id = self.storage.insert(store)
        return store.record_id

    def load_all(self) -> dict:
        """
        Load stores from DB

        :return: stores dict
        """
        return self.storage.get_all()

    def load(self, id: int) -> AssistantStoreItem:
        """
        Load store from DB

        :param id: store ID
        :return: store item
        """
        return self.storage.get_by_id(id)

    def save(self, store: AssistantStoreItem):
        """
        Save store to DB

        :param store: AssistantStoreItem
        """
        try:
            self.storage.save(store)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving stored: {}".format(str(e)))

    def save_all(self, items: dict):
        """
        Save all stores to DB

        :param items: dict of AssistantStoreItem objects
        """
        try:
            for id in items:
                store = items[id]
                self.storage.save(store)
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error while saving store: {}".format(str(e)))

    def delete_by_id(self, id: int) -> bool:
        """
        Delete store item by IDx

        :param id: store item ID
        :return: True if deleted
        """
        return self.storage.delete_by_id(id)

    def delete_by_store_id(self, id: str) -> bool:
        """
        Delete store item by IDx

        :param id: store_id
        :return: True if deleted
        """
        return self.storage.delete_by_store_id(id)

    def truncate(self) -> bool:
        """
        Truncate all stores

        :return: True if truncated
        """
        return self.storage.truncate_all()


