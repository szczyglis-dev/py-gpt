#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This store is a part of PYGPT package              #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import time
from typing import Dict

from sqlalchemy import text

from pygpt_net.item.assistant import AssistantStoreItem

from .utils import pack_item_value, unpack_store

class Storage:
    def __init__(self, window=None):
        """
        Initialize storage instance

        :param window: Window instance
        """
        self.window = window

    def attach(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def get_all(self) -> Dict[str, AssistantStoreItem]:
        """
        Return dict with AssistantStoreItem objects, indexed by ID

        :return: dict of AssistantStoreItem objects
        """
        stmt = text("""
            SELECT * FROM remote_store
        """)
        items = {}
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                store = AssistantStoreItem()
                unpack_store(store, row._asdict())
                items[store.id] = store  # index by store ID
        return items

    def get_by_id(self, id: int) -> AssistantStoreItem:
        """
        Return AssistantStoreItem by ID

        :param id: store item ID
        :return: AssistantStoreItem
        """
        stmt = text("""
            SELECT * FROM remote_store WHERE id = :id LIMIT 1
        """).bindparams(id=id)
        store = AssistantStoreItem()
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                unpack_store(store, row._asdict())
        return store

    def get_by_store_id(self, id: str) -> AssistantStoreItem:
        """
        Return AssistantStoreItem by ID

        :param id: store_id
        :return: AssistantStoreItem
        """
        stmt = text("""
            SELECT * FROM remote_store WHERE store_id = :id LIMIT 1
        """).bindparams(id=id)
        store = AssistantStoreItem()
        db = self.window.core.db.get_db()
        with db.connect() as conn:
            result = conn.execute(stmt)
            for row in result:
                unpack_store(store, row._asdict())
        return store

    def truncate_all(self) -> bool:
        """
        Truncate all stores items

        :return: True if truncated
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(text("DELETE FROM remote_store"))
            conn.execute(text("DELETE FROM sqlite_sequence WHERE name='remote_store'"))
        return True

    def delete_by_id(self, id: int) -> bool:
        """
        Delete store item by IDx

        :param id: store item ID
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM remote_store WHERE id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def delete_by_store_id(self, id: str) -> bool:
        """
        Delete store item by IDx

        :param id: store_id
        :return: True if deleted
        """
        stmt = text("""
            DELETE FROM remote_store WHERE store_id = :id
        """).bindparams(id=id)
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            conn.execute(stmt)
            return True

    def save(self, store: AssistantStoreItem):
        """
        Insert or update store item

        :param store: AssistantStoreItem object
        """
        db = self.window.core.db.get_db()
        with db.begin() as conn:
            ts = int(time.time())
            stmt = text("""
                UPDATE remote_store
                SET
                    name = :name,
                    description = :description,
                    expire_days = :expire_days,
                    usage_bytes = :usage_bytes,
                    num_files = :num_files,
                    store_id = :store_id,
                    status = :status,
                    status_json = :status_json,
                    is_thread = :is_thread,
                    last_active_ts = :last_active_ts,
                    last_sync_ts = :last_sync_ts,
                    updated_ts = :updated_ts
                WHERE id = :id
                """).bindparams(
                id=store.record_id,
                name=store.name,
                description=store.description,
                expire_days=store.expire_days,
                usage_bytes=store.usage_bytes,
                num_files=store.num_files,
                store_id=store.id,
                status=store.last_status,
                status_json=pack_item_value(store.status),
                is_thread=store.is_thread,
                last_active_ts=store.last_active,
                last_sync_ts=store.last_sync,
                updated_ts=ts
            )
            conn.execute(stmt)

    def insert(self, store: AssistantStoreItem) -> int:
        """
        Insert store item

        :param store: AssistantStoreItem object
        :return: store item ID
        """
        db = self.window.core.db.get_db()
        ts = int(time.time())
        stmt = text("""
            INSERT INTO remote_store
            (
                store_id,
                uuid,
                name,
                description,
                expire_days,
                usage_bytes,
                num_files,
                status,
                status_json,
                is_thread,
                last_active_ts,
                last_sync_ts,
                created_ts,
                updated_ts
            )
            VALUES
            (
                :store_id,
                :uuid,
                :name,
                :description,
                :expire_days,
                :usage_bytes,
                :num_files,
                :status,
                :status_json,
                :is_thread,
                :last_active_ts,
                :last_sync_ts,
                :created_ts,
                :updated_ts
            )
            """).bindparams(
            store_id=store.id,
            uuid=store.uuid,
            name=store.name,
            description=store.description,
            expire_days=int(store.expire_days or 0),
            usage_bytes=int(store.usage_bytes or 0),
            num_files=int(store.num_files or 0),
            status=store.last_status,
            status_json=pack_item_value(store.status),
            is_thread=int(store.is_thread or 0),
            last_active_ts=int(store.last_active or 0),
            last_sync_ts=int(store.last_sync or 0),
            created_ts=int(ts or 0),
            updated_ts=int(ts or 0),
        )
        with db.begin() as conn:
            result = conn.execute(stmt)
            store.record_id = result.lastrowid
            return store.record_id
