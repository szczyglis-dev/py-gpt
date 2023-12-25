#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #

from pygpt_net.core.provider.ctx.base import BaseProvider


class DbSqliteProvider(BaseProvider):
    def __init__(self):
        super(DbSqliteProvider, self).__init__()
        self.id = "db_sqlite"
        self.type = "ctx"

        # TODO: Implement sqlite provider and search methods
