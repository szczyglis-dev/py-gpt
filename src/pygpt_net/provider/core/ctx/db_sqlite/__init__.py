#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 04:00:00                  #
# ================================================== #

import time
from uuid import uuid4
from packaging.version import Version

from pygpt_net.item.ctx import CtxMeta, CtxItem
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

    def get_meta(self, search_string: str = None, order_by: str = None, order_direction: str = None,
                 limit: int = None, offset: int = None) -> dict:
        """
        Return dict of ctx meta, TODO: add order, limit, offset, etc.

        :param search_string: search string
        :param order_by: order by column
        :param order_direction: order direction
        :param limit: limit
        :param offset: offset
        :return: dict of ctx meta
        """
        param_limit = 0
        if limit is not None:
            param_limit = int(limit)
        return self.storage.get_meta(search_string, order_by, order_direction, param_limit, offset)

    def load(self, id: int) -> list:
        """
        Load items for ctx ID

        :param id: ctx ID
        :return: list of ctx items
        """
        return self.storage.get_items(id)

    def get_ctx_count_by_day(self, year, month) -> dict:
        """
        Get ctx count by day

        :param year: year
        :param month: month
        :return: dict of ctx counters by day
        """
        return self.storage.get_ctx_count_by_day(year, month)

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

    def remove(self, id: int) -> bool:
        """
        Remove ctx

        :param id: ctx meta ID
        :return: True if removed
        """
        return self.storage.delete_meta_by_id(id)

    def truncate(self) -> bool:
        """
        Truncate ctx (remove all ctx, meta + items)

        :return: True if truncated
        """
        return self.storage.truncate_all()
