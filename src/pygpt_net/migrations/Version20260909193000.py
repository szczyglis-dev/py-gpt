#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 19:45:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20260909193000(BaseMigration):
    def __init__(self, window=None):
        super(Version20260909193000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            updated_at INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT ''
        );
        """))
        # SQLite UNIQUE(project_id) allows multiple NULL values. The expression
        # index maps NULL (global scope) to -1 so there can be only one global
        # row and one row for each positive project/group ID.
        conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_scope_unique
        ON memory (COALESCE(project_id, -1));
        """))
