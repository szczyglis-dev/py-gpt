#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 11:00:00                  #
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

        self.window.core.debug.add(self.id, 'Storage:', str(list(self.window.core.idx.storage.indexes.keys())))

        # indexes
        indexes = self.window.core.idx.get_all()
        for key in list(indexes):
            path = os.path.join(self.window.core.config.get_user_dir('idx'), key)
            idx = indexes[key]
            self.window.core.debug.add(self.id, '----', '')
            self.window.core.debug.add(self.id, 'IDX: [' + str(key) + ']', '')
            self.window.core.debug.add(self.id, 'PATH:', str(path))
            self.window.core.debug.add(self.id, '- id', str(idx.id))
            self.window.core.debug.add(self.id, '- name', str(idx.name))

            items = idx.items
            self.window.core.debug.add(self.id, 'len(items)', str(len(items)))
            for item_id in items:
                item = items[item_id]
                indexed_dt = datetime.datetime.fromtimestamp(item['indexed_ts'])
                self.window.core.debug.add(self.id, '>>> [' + str(item_id) + ']', '')
                self.window.core.debug.add(self.id, ' --- id', str(item['id']))
                self.window.core.debug.add(self.id, ' --- path', str(item['path']))
                self.window.core.debug.add(self.id, ' --- indexed_at', str(item['indexed_ts'])
                                           + ' (' + str(indexed_dt) + ')')

        self.window.core.debug.end(self.id)
