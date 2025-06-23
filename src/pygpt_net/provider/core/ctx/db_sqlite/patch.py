#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.23 19:00:00                  #
# ================================================== #

import datetime
import os
import shutil
import sys

from packaging.version import parse as parse_version, Version

from pygpt_net.item.ctx import CtxMeta


class Patch:
    def __init__(self, window=None, provider=None):
        self.window = window
        self.provider = provider

    def execute(self, version: Version) -> bool:
        """
        Migrate to current app version

        :param version: current app version
        :return: True if migrated
        """
        # return
        # if old version is 2.0.59 or older and if json file exists
        path = os.path.join(self.window.core.config.path, 'context.json')
        if os.path.exists(path):
            self.provider.truncate()
            self.import_from_json()
            # rename context.json to context.json.old:
            os.rename(path, path + ".old")
            return True

    def import_from_json(self) -> bool:
        """
        Import ctx from JSON

        :return: True if imported
        """
        return True
        # use json provider to load old contexts
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

    def import_ctx(self, meta: CtxMeta, items: list):
        """
        Import ctx from JSON

        :param meta: ctx meta (CtxMeta)
        :param items: list of ctx items (CtxItem)
        """
        meta.id = None  # reset old meta ID to allow creating new
        self.provider.create(meta)  # create new meta and get its new ID
        for item in items:
            self.provider.storage.insert_item(meta, item)  # append items to new meta
