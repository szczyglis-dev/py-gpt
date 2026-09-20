#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.14 18:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20260914180000(BaseMigration):
    """Per-conversation compact continuation memory for advanced context handling."""

    def __init__(self, window=None):
        super(Version20260914180000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_ctx (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_id INTEGER NOT NULL,
            updated_at INTEGER NOT NULL DEFAULT 0,
            last_item_id INTEGER NOT NULL DEFAULT 0,
            generation INTEGER NOT NULL DEFAULT 0,
            revision INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(meta_id) REFERENCES ctx_meta(id) ON DELETE CASCADE
        );
        """))
        conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_ctx_meta_unique
        ON memory_ctx (meta_id);
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_memory_ctx_updated_at
        ON memory_ctx (updated_at);
        """))
