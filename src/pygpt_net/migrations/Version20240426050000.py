#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20240426050000(BaseMigration):
    def __init__(self, window=None):
        super(Version20240426050000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS remote_file (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            store_id TEXT,
            thread_id TEXT,
            uuid TEXT,
            name TEXT,
            path TEXT,
            size INT,
            created_ts INTEGER,
            updated_ts INTEGER
        );
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS remote_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            uuid TEXT,
            name TEXT,
            expire_days INT,
            usage_bytes INT,
            num_files INT,
            description TEXT,
            status TEXT,
            status_json TEXT,
            last_active_ts INTEGER,
            last_sync_ts INTEGER,
            is_thread BOOLEAN NOT NULL DEFAULT 0 CHECK (is_thread IN (0, 1)),
            created_ts INTEGER,
            updated_ts INTEGER
        );
        """))
