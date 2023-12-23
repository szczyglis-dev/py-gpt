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


class ContextMeta:
    def __init__(self, id=None):
        """
        Context meta data
        """
        self.id = id
        self.name = None
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.mode = None
        self.last_mode = None
        self.thread = None
        self.assistant = None
        self.preset = None
        self.run = None
        self.status = None
        self.initialized = False

