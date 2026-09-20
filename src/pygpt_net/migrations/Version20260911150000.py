#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 15:15:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20260911150000(BaseMigration):
    def __init__(self, window=None):
        super(Version20260911150000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            key TEXT NOT NULL,
            updated_at INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT ''
        );
        """))
        # Keep key names unique inside each scope. COALESCE maps NULL (global
        # scope) to -1, matching the scope semantics used by the memory table.
        conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_keys_scope_key_unique
        ON memory_keys (COALESCE(project_id, -1), key);
        """))
        # Prefixing LIKE with '%' prevents an ordinary key index from being
        # useful for the text match itself, but indexing the scope keeps project
        # filtering cheap before the LIKE scan is applied.
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_memory_keys_project_id
        ON memory_keys (project_id);
        """))
