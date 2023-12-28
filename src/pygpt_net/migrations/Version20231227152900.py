#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.27 21:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20231227152900(BaseMigration):
    def __init__(self, window=None):
        super(Version20231227152900, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ctx_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT,
            uuid TEXT,
            created_ts INTEGER,
            updated_ts INTEGER,
            name TEXT,
            mode TEXT,
            model TEXT,
            last_mode TEXT,
            last_model TEXT,
            thread_id TEXT,
            assistant_id TEXT,
            preset_id TEXT,
            run_id TEXT,
            status TEXT,
            extra TEXT,
            is_initialized BOOLEAN NOT NULL CHECK (is_initialized IN (0, 1)),
            is_deleted BOOLEAN NOT NULL CHECK (is_deleted IN (0, 1)),
            is_important BOOLEAN NOT NULL CHECK (is_important IN (0, 1)),
            is_archived BOOLEAN NOT NULL CHECK (is_archived IN (0, 1))
        );"""))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ctx_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT,
            meta_id INTEGER,
            input TEXT,
            output TEXT,
            input_name TEXT,
            output_name TEXT,
            input_ts INTEGER,
            output_ts INTEGER,
            mode TEXT,
            model TEXT,
            thread_id TEXT,
            msg_id TEXT,
            run_id TEXT,
            cmds_json TEXT,
            results_json TEXT,
            urls_json TEXT,
            images_json TEXT,
            files_json TEXT,
            attachments_json TEXT,
            extra TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            FOREIGN KEY(meta_id) REFERENCES ctx_meta(id) ON DELETE SET NULL
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS notepad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idx INTEGER,
            uuid TEXT,
            created_ts INTEGER,
            updated_ts INTEGER,
            title TEXT,
            content TEXT,
            is_deleted BOOLEAN NOT NULL CHECK (is_deleted IN (0, 1))
        );"""))
