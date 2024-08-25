#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

import datetime


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
        self.window.core.debug.add(self.id, 'Current mode:', str(self.window.controller.idx.current_mode))
        self.window.core.debug.add(self.id, 'Chat mode:', str(self.window.core.config.get("llama.idx.chat.mode")))
        self.window.core.debug.add(self.id, 'Indexes (list):', str(list(self.window.core.config.get("llama.idx.list"))))

        # count items in DB
        db_counter = {}
        db_counter["ctx"] = self.window.core.idx.get_counters("ctx")
        db_counter["file"] = self.window.core.idx.get_counters("file")
        db_counter["external"] = self.window.core.idx.get_counters("external")

        for store in self.window.core.idx.items:
            name = "Items (files): " + store
            indexes_data = {}
            for idx in self.window.core.idx.items[store]:
                indexes_data[idx] = len(self.window.core.idx.items[store][idx].items)
            if len(indexes_data) > 0:
                self.window.core.debug.add(self.id, name, str(indexes_data))

        # DB items counters
        self.window.core.debug.add(self.id, 'DB items (ctx):',
                                   str(db_counter["ctx"]))
        self.window.core.debug.add(self.id, 'DB items (external/web):',
                                   str(db_counter["external"]))
        self.window.core.debug.add(self.id, 'DB items (file):',
                                   str(db_counter["file"]))

        self.window.core.debug.add(self.id, 'Storage (storages):',
                                   str(list(self.window.core.idx.storage.storages.keys())))
        self.window.core.debug.add(self.id, 'Temp (in-memory) indices:',
                                   str(self.window.core.idx.storage.count_tmp()))

        # loaders
        self.window.core.debug.add(self.id, 'Offline loaders [files]:',
                                   str(sorted(list(self.window.core.idx.indexing.loaders["file"].keys()))))
        self.window.core.debug.add(self.id, 'Offline loaders [web]:',
                                   str(sorted(list(self.window.core.idx.indexing.loaders["web"].keys()))))
        self.window.core.debug.add(self.id, 'External instructions [web]:',
                                   str(self.window.core.idx.indexing.external_instructions))

        excluded = self.window.core.config.get("llama.idx.excluded.ext").replace(" ", "").split(',')
        self.window.core.debug.add(self.id, 'Excluded (ext):', str(excluded))
        self.window.core.debug.add(self.id, 'Force exclude:',
                                   str(self.window.core.config.get("llama.idx.excluded.force")))
        self.window.core.debug.add(self.id, 'Custom metadata:',
                                   str(self.window.core.config.get("llama.idx.custom_meta")))

        # ctx
        self.window.core.debug.add(self.id, 'CTX [auto]:',
                                   str(self.window.core.config.get("llama.idx.auto")))
        last_str = "-"
        last_ctx = int(self.window.core.config.get("llama.idx.db.last"))
        if last_ctx > 0:
            last_str = datetime.datetime.fromtimestamp(last_ctx).strftime('%Y-%m-%d %H:%M:%S') + " (" + str(last_ctx) + ")"
        self.window.core.debug.add(self.id, 'CTX [db.last]:', str(last_str))

        # indexes
        """
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
        """

        self.window.core.debug.end(self.id)
