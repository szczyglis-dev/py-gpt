#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.07 12:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20260907120000(BaseMigration):
    def __init__(self, window=None):
        super(Version20260907120000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ctx_item_partial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT NOT NULL,
            parent_item_id INTEGER NOT NULL,
            agent_id TEXT,
            name TEXT,
            output TEXT,
            extra_json TEXT,
            created_at INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(parent_item_id) REFERENCES ctx_item(id) ON DELETE CASCADE
        );
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ctx_item_partial_parent
        ON ctx_item_partial(parent_item_id, id);
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ctx_item_partial_uuid
        ON ctx_item_partial(uuid);
        """))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ctx_item_partial_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT NOT NULL,
            parent_item_part_id INTEGER NOT NULL,
            agent_id TEXT,
            name TEXT,
            task_name TEXT,
            task_summary TEXT,
            input TEXT,
            output TEXT,
            tool_call_id TEXT,
            tool_input_json TEXT,
            tool_output_json TEXT,
            extra_json TEXT,
            created_at INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(parent_item_part_id) REFERENCES ctx_item_partial(id) ON DELETE CASCADE
        );
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ctx_item_partial_task_parent
        ON ctx_item_partial_task(parent_item_part_id, id);
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ctx_item_partial_task_call
        ON ctx_item_partial_task(tool_call_id);
        """))
        conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_ctx_item_partial_task_uuid
        ON ctx_item_partial_task(uuid);
        """))
