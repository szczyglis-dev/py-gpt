#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        idx_core = self.window.core.idx
        idx_controller = self.window.controller.idx
        config = self.window.core.config
        storage = idx_core.storage
        indexing = idx_core.indexing

        debug.begin(self.id)
        debug.add(self.id, 'Current storage:', str(idx_core.get_current_store()))
        debug.add(self.id, 'Current idx:', str(idx_controller.current_idx))
        debug.add(self.id, 'Current mode:', str(idx_controller.current_mode))
        debug.add(self.id, 'Chat mode:', str(config.get("llama.idx.chat.mode")))
        debug.add(self.id, 'Indexes (list):', str(list(config.get("llama.idx.list"))))

        # count items in DB
        db_counter = {
            "ctx": idx_core.get_counters("ctx"),
            "file": idx_core.get_counters("file"),
            "external": idx_core.get_counters("external")
        }

        for store in idx_core.items:
            name = "Items (files): " + store
            indexes_data = {idx: len(idx_core.items[store][idx].items)
                            for idx in idx_core.items[store]}
            if indexes_data:
                debug.add(self.id, name, str(indexes_data))

        # DB items counters
        debug.add(self.id, 'DB items (ctx):', str(db_counter["ctx"]))
        debug.add(self.id, 'DB items (external/web):', str(db_counter["external"]))
        debug.add(self.id, 'DB items (file):', str(db_counter["file"]))

        debug.add(self.id, 'Storage (storages):', str(list(storage.storages.keys())))
        debug.add(self.id, 'Temp (in-memory) indices:', str(storage.count_tmp()))

        # loaders
        debug.add(self.id, 'Offline loaders [files]:', str(sorted(list(indexing.loaders["file"].keys()))))
        debug.add(self.id, 'Offline loaders [web]:', str(sorted(list(indexing.loaders["web"].keys()))))
        debug.add(self.id, 'External instructions [web]:', str(indexing.external_instructions))

        excluded = config.get("llama.idx.excluded.ext").replace(" ", "").split(',')
        debug.add(self.id, 'Excluded (ext):', str(excluded))
        debug.add(self.id, 'Force exclude:', str(config.get("llama.idx.excluded.force")))
        debug.add(self.id, 'Custom metadata:', str(config.get("llama.idx.custom_meta")))

        # ctx
        debug.add(self.id, 'CTX [auto]:', str(config.get("llama.idx.auto")))
        last_ctx = int(config.get("llama.idx.db.last"))
        last_str = "-" if last_ctx <= 0 else f"{datetime.datetime.fromtimestamp(last_ctx).strftime('%Y-%m-%d %H:%M:%S')} ({last_ctx})"
        debug.add(self.id, 'CTX [db.last]:', str(last_str))

        debug.end(self.id)
