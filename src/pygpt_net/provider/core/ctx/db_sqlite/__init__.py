#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import time
from uuid import uuid4
from packaging.version import Version

from pygpt_net.item.ctx import CtxMeta, CtxItem, CtxGroup
from .patch import Patch
from .storage import Storage
from pygpt_net.provider.core.ctx.base import BaseProvider


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window, self)
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "ctx"

    def attach(self, window):
        self.window = window
        self.storage.attach(window)

    def patch(self, version: Version):
        """
        Patch versions

        :param version: current app version
        """
        return self.patcher.execute(version)

    def create_id(self, meta: CtxMeta) -> int:
        """
        Create ctx ID

        :return: generated ID
        """
        return self.storage.insert_meta(meta)

    def create(self, meta: CtxMeta) -> int:
        """
        Create new ctx and return its ID

        :param meta: CtxMeta
        :return: ctx ID
        """
        ts = int(time.time())
        if meta.uuid is None:
            meta.uuid = str(uuid4())
        if meta.created is None:
            meta.created = ts
        if meta.updated is None:
            meta.updated = ts
        if meta.id is None:
            meta.id = self.create_id(meta)  # insert to DB and get ID
        return meta.id

    def get_meta(
            self,
            search_string: str = None,
            order_by: str = None,
            order_direction: str = None,
            limit: int = None,
            offset: int = None,
            filters: dict = None,
            search_content: bool = False,
    ) -> dict:
        """
        Return dict of ctx meta, TODO: add order, limit, offset, etc.

        :param search_string: search string
        :param order_by: order by column
        :param order_direction: order direction (asc, desc)
        :param limit: limit
        :param offset: offset
        :param filters: filters
        :param search_content: search in content (not only in meta)
        :return: dict of ctx meta
        """
        param_limit = 0
        if limit is not None:
            param_limit = int(limit)

        return self.storage.get_meta(
            search_string=search_string,
            order_by=order_by,
            order_direction=order_direction,
            limit=param_limit,
            offset=offset,
            filters=filters,
            search_content=search_content,
        )

    def get_meta_indexed(self) -> dict:
        """
        Return dict of ctx meta indexed by ID

        :return: dict of ctx meta indexed by ID
        """
        return self.storage.get_meta_indexed()

    def get_last_meta_id(self) -> int:
        """
        Get last meta ID

        :return: last meta ID
        """
        return self.storage.get_last_meta_id()

    def load(self, id: int) -> list:
        """
        Load items for ctx ID

        :param id: ctx ID
        :return: list of ctx items
        """
        return self.storage.get_items(id)

    def get_ctx_count_by_day(
            self, year: int,
            month: int = None,
            day: int = None,
            search_string: str = None,
            filters: dict = None,
            search_content: bool = False,
    ) -> dict:
        """
        Get ctx count by day or by month if only year is provided

        :param year: year
        :param month: month
        :param day: day
        :param search_string: search string (optional)
        :param filters: filters (optional)
        :param search_content: search in content (not only in meta) (optional)
        :return: dict of ctx counters by day or by month if only year is provided
        """
        return self.storage.get_ctx_count_by_day(
            year=year,
            month=month,
            day=day,
            search_string=search_string,
            filters=filters,
            search_content=search_content,
        )

    def append_item(self, meta: CtxMeta, item: CtxItem) -> bool:
        """
        Append item to ctx

        :param meta: ctx meta (CtxMeta)
        :param item: ctx item (CtxItem)
        :return: True if appended
        """
        self.storage.update_meta_ts(meta.id)
        return self.storage.insert_item(meta, item) is not None

    def update_item(self, item: CtxItem) -> bool:
        """
        Update item in ctx

        :param item: ctx item (CtxItem)
        :return: True if updated
        """
        self.storage.update_meta_ts(item.meta_id)
        return self.storage.update_item(item) is not None

    def save(self, id: int, meta: CtxMeta, items: list) -> bool:
        """
        Save ctx

        :param id: ctx ID
        :param meta: CtxMeta
        :param items: list of CtxItem
        :return: True if saved
        """
        if self.storage.update_meta(meta):
            return True  # update only meta, items are appended separately

    def save_all(self, id: int, meta: CtxMeta, items: list) -> bool:
        """
        Save ctx

        :param id: ctx ID
        :param meta: CtxMeta
        :param items: list of CtxItem
        :return: True if saved
        """
        if self.storage.update_meta_all(meta, items):
            return True

    def remove(self, id: int) -> bool:
        """
        Remove ctx (meta + items)

        :param id: ctx meta ID
        :return: True if removed
        """
        return self.storage.delete_meta_by_id(id)

    def remove_item(self, id: int) -> bool:
        """
        Remove ctx item

        :param id: ctx item ID
        :return: True if removed
        """
        return self.storage.delete_item_by_id(id)

    def remove_items_from(self, meta_id: int, item_id: int):
        """
        Remove ctx items from meta_id

        :param meta_id: meta_id
        :param item_id: item_id
        :return: True if removed
        """
        return self.storage.delete_items_from(meta_id, item_id)

    def truncate(self) -> bool:
        """
        Truncate ctx (remove all ctx, meta + items)

        :return: True if truncated
        """
        return self.storage.truncate_all()

    def set_meta_indexed_by_id(self, id: int, ts: int) -> bool:
        """
        Set meta indexed by ID

        :param id: ctx ID
        :param ts: timestamp
        :return: True if set
        """
        return self.storage.set_meta_indexed_by_id(id, ts)

    def update_meta_indexes_by_id(self, id: int, meta: CtxMeta) -> bool:
        """
        Update meta indexes by ID

        :param id: ctx ID
        :param meta: CtxMeta
        :return: True if updated
        """
        return self.storage.update_meta_indexes_by_id(id, meta)

    def update_meta_indexed_by_id(self, id: int) -> bool:
        """
        Update meta indexed timestamp by ID

        :param id: ctx ID
        :return: True if updated
        """
        return self.storage.update_meta_indexed_by_id(id)

    def update_meta_indexed_to_ts(self, ts: int) -> bool:
        """
        Update meta indexed to timestamp

        :param ts: timestamp
        :return: True if updated
        """
        return self.storage.update_meta_indexed_to_ts(ts)

    def clear_meta_indexed_by_id(self, id: int) -> bool:
        """
        Clear meta indexed timestamp by ID

        :param id: ctx ID
        :return: True if cleared
        """
        return self.storage.clear_meta_indexed_by_id(id)

    def clear_meta_indexed_all(self) -> bool:
        """
        Clear all meta indexed timestamps

        :return: True if cleared
        """
        return self.storage.clear_meta_indexed_all()

    def get_groups(self) -> dict:
        """
        Return dict of groups

        :return: dict of ctx meta
        """
        return self.storage.get_groups()

    def get_meta_by_id(self, id: int) -> CtxMeta or None:
        """
        Get meta by ID

        :param id: ctx ID
        """
        return self.storage.get_meta_by_id(id)

    def get_meta_by_root_id_and_preset_id(self, root_id: int, preset_id: str):
        """
        Get meta by root ID and preset ID

        :param root_id: root ID
        :param preset_id: preset ID
        """
        return self.storage.get_meta_by_root_id_and_preset_id(root_id, preset_id)

    def insert_group(self, group: CtxGroup):
        """
        Insert group

        :param group: CtxGroup
        """
        return self.storage.insert_group(group)

    def update_group(self, group: CtxGroup):
        """
        Update group

        :param group: CtxGroup
        """
        return self.storage.update_group(group)

    def remove_group(self, id: int, all: bool = False):
        """
        Remove group by ID

        :param id: group ID
        :param all: remove items
        """
        return self.storage.delete_group(id, all=all)

    def truncate_groups(self):
        """Remove groups"""
        return self.storage.truncate_groups()

    def update_meta_group_id(self, id: int, group_id: int):
        """
        Update meta group ID

        :param id: ctx ID
        :param group_id: group ID
        """
        return self.storage.update_meta_group_id(id, group_id)
