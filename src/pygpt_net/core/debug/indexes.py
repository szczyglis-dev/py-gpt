#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
# ================================================== #

import datetime
import os


class IndexesDebug:
    def __init__(self, window=None):
        """
        Indexes debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'indexes'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)
        self.window.core.debug.add(self.id, 'Current storage:', str(self.window.core.idx.get_current_store()))
        self.window.core.debug.add(self.id, 'Current idx:', str(self.window.controller.idx.current_idx))

        for store in self.window.core.idx.items:
            name = "Items (files): " + store
            indexes_data = {}
            for idx in self.window.core.idx.items[store]:
                indexes_data[idx] = len(self.window.core.idx.items[store][idx].items)
            if len(indexes_data) > 0:
                self.window.core.debug.add(self.id, name, str(indexes_data))

        self.window.core.debug.add(self.id, 'Storage (idx):',
                                   str(list(self.window.core.idx.storage.indexes.keys())))
        self.window.core.debug.add(self.id, 'Storage (storage):',
                                   str(list(self.window.core.idx.storage.storages.keys())))

        # loaders
        self.window.core.debug.add(self.id, 'Offline loaders [files]:',
                                   str(list(self.window.core.idx.indexing.loaders["file"].keys())))
        self.window.core.debug.add(self.id, 'Offline loaders [web]:',
                                   str(list(self.window.core.idx.indexing.loaders["web"].keys())))
        self.window.core.debug.add(self.id, 'External instructions [web]:',
                                   str(self.window.core.idx.indexing.external_instructions))

        # indexes
        indexes = self.window.core.idx.get_all()
        for key in list(indexes):
            path = os.path.join(self.window.core.config.get_user_dir('idx'), key)
            idx = indexes[key]
            self.window.core.debug.add(self.id, '----', '')
            idx_data = {
                'id': idx.id,
                'store': idx.store,
                'path': path,
                'items': len(idx.items),
            }
            self.window.core.debug.add(self.id, 'IDX: [' + str(key) + ']', str(idx_data))

            # files
            items = idx.items
            for item_id in items:
                item = items[item_id]
                indexed_dt = datetime.datetime.fromtimestamp(item['indexed_ts'])
                data = {
                    'id': item['id'],
                    'path': item['path'],
                    'indexed_at': str(item['indexed_ts']) + ' (' + str(indexed_dt) + ')',
                    'file_id': item_id,
                }
                self.window.core.debug.add(self.id, item_id, str(data))

        self.window.core.debug.end(self.id)
