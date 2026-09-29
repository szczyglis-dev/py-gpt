#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 17:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20260904170000(BaseMigration):
    def __init__(self, window=None):
        super(Version20260904170000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS idx_proj (
            group_id INTEGER PRIMARY KEY,
            idx_id TEXT NOT NULL,
            last_meta INTEGER DEFAULT 0,
            last_item INTEGER DEFAULT 0,
            last_update INTEGER DEFAULT 0,
            FOREIGN KEY(group_id) REFERENCES ctx_group(id) ON DELETE CASCADE
        );
        """))
