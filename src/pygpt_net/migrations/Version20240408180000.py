#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.08 21:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20240408180000(BaseMigration):
    def __init__(self, window=None):
        super(Version20240408180000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ctx_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            name TEXT,
            created_ts INTEGER,
            updated_ts INTEGER
        );
        """))
        conn.execute(text("""
        ALTER TABLE ctx_meta ADD COLUMN group_id INTEGER;
        """))
