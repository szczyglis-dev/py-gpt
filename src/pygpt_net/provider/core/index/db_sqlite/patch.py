#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 06:00:00                  #
# ================================================== #

import os
import shutil
import sys

from packaging.version import parse as parse_version, Version


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
        # if old version is < 2.0.162 and if json file exists
        path = os.path.join(self.window.core.config.path, 'indexes.json')
        if os.path.exists(path):
            self.provider.truncate_all()
            self.import_from_json()
            os.rename(path, path + ".old")  # rename to "indexes.json.old"
            print("BACKUP: indexes.json file has been renamed to indexes.json.old")
            return True

    def import_from_json(self) -> bool:
        """
        Import idx data from JSON

        :return: True if imported
        """
        # use old json provider to load old indexes
        provider = self.window.core.idx.providers['json_file']
        provider.attach(self.window)

        print("[DB] Migrating idx into database storage...")
        print("[DB] Importing old idx data from JSON files... this may take a while. Please wait...")

        stores = provider.load()
        cols, _ = shutil.get_terminal_size()
        all = 0
        for store_id in stores:
            store = stores[store_id]
            c = len(store)
            i = 0
            for idx_id in store:
                idx = store[idx_id]
                line = "[DB] %s - importing idx %s/%s: %s" % (store_id, i + 1, c, idx.name)
                print(f"{line:<{cols}}", end='\r')
                sys.stdout.flush()
                self.import_idx(
                    store_id,
                    idx_id,
                    idx.items,
                )
                i += 1
                all += 1
                print()  # new line

        if all > 0:
            print("[DB] [DONE] Imported %s indexes." % all)
            return True

    def import_idx(self, store_id: str, idx_id: str, items: list) -> bool:
        """
        Import index data from JSON

        :param store_id: store ID
        :param idx_id: idx ID
        :param items: list of items
        """
        for file_id in items:
            item = items[file_id]
            self.provider.append_file(store_id, idx_id, item)
        return True
