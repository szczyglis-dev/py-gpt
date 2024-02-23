#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 01:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20240222160000(BaseMigration):
    def __init__(self, window=None):
        super(Version20240222160000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS idx_file (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            doc_id TEXT,
            created_ts INTEGER,
            updated_ts INTEGER,
            name TEXT,
            path TEXT,
            store TEXT,
            idx TEXT
        );"""))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS idx_ctx (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            doc_id TEXT,
            meta_id INTEGER,
            created_ts INTEGER,
            updated_ts INTEGER,
            store TEXT,
            idx TEXT,
            FOREIGN KEY(meta_id) REFERENCES ctx_meta(id) ON DELETE SET NULL
        );
        """))

        conn.execute(text("""
        ALTER TABLE ctx_meta ADD COLUMN indexed_ts INTEGER NOT NULL DEFAULT 0;
        """))

        conn.execute(text("""
        ALTER TABLE ctx_meta ADD COLUMN indexes_json TEXT NOT NULL DEFAULT '{}';
        """))
