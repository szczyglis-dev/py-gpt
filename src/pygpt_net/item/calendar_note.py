#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

import datetime
import time


class CalendarNoteItem:
    def __init__(self):
        self.id = 0
        self.uuid = None
        self.idx = 0
        self.year = 0
        self.month = 0
        self.day = 0
        self.status = 0
        self.title = ""
        self.content = ""
        self.deleted = False
        ts = int(time.time())
        self.created = ts
        self.updated = ts
        self.important = False
        self.initialized = False
        self.deleted = False

    def get_dt(self) -> str:
        """
        Convert year, month, day to key string in format: YYYY-MM-DD
        :return: key string in format: YYYY-MM-DD
        """
        return datetime.datetime(self.year, self.month, self.day).strftime("%Y-%m-%d")
