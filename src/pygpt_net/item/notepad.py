#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import time


class NotepadItem:
    def __init__(self):
        self.id = 0
        self.uuid = None
        self.idx = 0
        self.title = ""
        self.content = ""
        self.deleted = False
        ts = int(time.time())
        self.created = ts
        self.updated = ts
