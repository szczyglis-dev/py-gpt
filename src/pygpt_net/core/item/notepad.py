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


class NotepadItem:
    def __init__(self):
        self.id = None
        self.idx = 0
        self.title = ""
        self.content = ""
        self.created_at = None
        self.updated_at = None
