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

from sqlalchemy import text

from .base import BaseMigration


class Version20240223050000(BaseMigration):
    def __init__(self, window=None):
        super(Version20240223050000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS idx_external (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            doc_id TEXT,
            created_ts INTEGER,
            updated_ts INTEGER,
            content TEXT,
            type TEXT,
            store TEXT,
            idx TEXT
        );"""))
