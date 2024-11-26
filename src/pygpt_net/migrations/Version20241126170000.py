#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 19:00:00                  #
# ================================================== #

from sqlalchemy import text

from .base import BaseMigration


class Version20241126170000(BaseMigration):
    def __init__(self, window=None):
        super(Version20241126170000, self).__init__(window)
        self.window = window

    def up(self, conn):
        conn.execute(text("""
        ALTER TABLE ctx_item ADD COLUMN audio_id TEXT;
        """))
        conn.execute(text("""
        ALTER TABLE ctx_item ADD COLUMN audio_expires_ts INTEGER;
        """))
