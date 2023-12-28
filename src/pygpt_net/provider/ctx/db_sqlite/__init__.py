#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.27 14:00:00                  #
# ================================================== #
import datetime
import os
import sys
import time
import shutil
from uuid import uuid4

from .storage import Storage
from pygpt_net.provider.ctx.base import BaseProvider


class DbSqliteProvider(BaseProvider):
    def __init__(self, window=None):
        super(DbSqliteProvider, self).__init__(window)
        self.window = window
        self.storage = Storage(window)
        self.id = "db_sqlite"
        self.type = "ctx"

    def attach(self, window):
        self.window = window
        self.storage.attach(window)

    def patch(self, version):
        """
        Patch versions

        :param version: current app version
        :return: true if migrated
        :rtype: bool
        """
        # return
        # if old version is 2.0.59 or older and if json file exists
        path = os.path.join(self.window.core.config.path, 'context.json')
        if os.path.exists(path):
            self.truncate()
            self.import_from_json()
            # rename context.json to context.json.old:
            os.rename(path, path + ".old")

    def create_id(self, meta):
        """
        Create unique ctx ID

        Format: YYYYMMDDHHMMSS.MICROSECONDS.json

        :return: generated ID
        :rtype: str
        """
        return self.storage.insert_meta(meta)

    def create(self, meta):
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

    def get_meta(self, search_string=None, order_by=None, order_direction=None, limit=None, offset=None):
        """
        Return dict of ctx meta, TODO: add order, limit, offset, etc.

        :param search_string: search string
        :param order_by: order by column
        :param order_direction: order direction
        :param limit: limit
        :param offset: offset

        :return: dict of ctx meta
        :rtype: dict
        """
        param_limit = 0
        if limit is not None:
            param_limit = int(limit)
        return self.storage.get_meta(search_string, order_by, order_direction, param_limit, offset)

    def load(self, id):
        """
        Load items for ctx ID

        :param id: ctx ID
        :return: list of ctx items
        :rtype: list
        """
        return self.storage.get_items(id)

    def append_item(self, meta, item):
        """
        Append item to ctx

        :param meta: ctx meta (CtxMeta)
        :param item: ctx item (CtxItem)
        """
        self.storage.update_meta_ts(meta.id)
        return self.storage.insert_item(meta, item) is not None

    def update_item(self, item):
        """
        Update item in ctx

        :param item: ctx item (CtxItem)
        :return: true if updated
        """
        self.storage.update_meta_ts(item.meta_id)
        return self.storage.update_item(item) is not None

    def save(self, id, meta, items):
        """
        Save ctx

        :param id: ctx ID
        :param meta: CtxMeta
        :param items: list of CtxItem
        :return: true if saved
        :rtype: bool
        """
        if self.storage.update_meta(meta):
            return True  # update only meta, items are appended separately

    def remove(self, id):
        """
        Remove ctx

        :param id: ctx meta ID
        :return: true if removed
        :rtype: bool
        """
        return self.storage.delete_meta_by_id(id)

    def truncate(self):
        """
        Truncate ctx (remove all ctx, meta + items)

        :return: true if truncated
        :rtype: bool
        """
        return self.storage.truncate_all()

    def import_from_json(self):
        """
        Import ctx from JSON

        :return: true if imported
        :rtype: bool
        """
        # return
        # tmp get json provider
        provider = self.window.core.ctx.providers['json_file']
        provider.attach(self.window)

        print("[DB] Migrating into database storage...")
        print("[DB] Importing old contexts from JSON files... this may take a while. Please wait...")
        i = 0
        metas = provider.get_meta()
        cols, _ = shutil.get_terminal_size()
        c = len(metas)
        for id in metas:
            meta = metas[id]
            line = "[DB] Importing context %s/%s: %s" % (i + 1, c, meta.name)
            print(f"{line:<{cols}}", end='\r')
            sys.stdout.flush()

            # update timestamp
            if len(id) == 21:
                date_format = "%Y%m%d%H%M%S.%f"
                dt = datetime.datetime.strptime(id, date_format)
                ts = dt.timestamp()
                meta.created = ts
                meta.updated = ts

            # load items
            items = provider.load(id)
            self.import_ctx(meta, items)
            i += 1

        print()  # new line

        if i > 0:
            print("[DB][DONE] Imported %s contexts." % i)
            return True

    def import_ctx(self, meta, items):
        """
        Import ctx from JSON

        :param meta: ctx meta (CtxMeta)
        :param items: list of ctx items (CtxItem)
        :return: true if imported
        :rtype: bool
        """
        meta.id = None  # reset old meta ID to allow creating new
        self.create(meta)  # create new meta and get its new ID
        for item in items:
            self.storage.insert_item(meta, item)  # append items to new meta
