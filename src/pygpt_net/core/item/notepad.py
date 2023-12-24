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
import datetime


class NotepadItem:
    def __init__(self):
        self.id = 0
        self.title = ""
        self.content = ""

        dt = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self.created_at = dt
        self.updated_at = dt
