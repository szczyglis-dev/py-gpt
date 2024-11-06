#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class PidData():

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.buffer = ""  # stream buffer
        self.is_cmd = False
        self.html = ""  # html buffer
        self.document = ""
        self.initialized = False
        self.loaded = False  # page loaded
        self.item = None  # current item
        self.use_buffer = False  # use html buffer
        self.name_user = trans("chat.name.user")
        self.name_bot = trans("chat.name.bot")
        self.last_time_called = 0
        self.cooldown = 1 / 6  # max chunks to parse per second
        self.throttling_min_chars = 5000  # min chunk chars to activate cooldown
