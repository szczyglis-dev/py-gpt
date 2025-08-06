#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.06 19:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class PidData:

    __slots__ = [
        'pid',                # Process ID
        'meta',               # CtxMeta instance
        'images_appended',    # Images appended to the PID
        'urls_appended',      # URLs appended to ctx
        'files_appended',     # Files appended to ctx
        'buffer',             # Stream buffer
        'live_buffer',        # Live stream buffer
        'is_cmd',             # Is command result
        'html',               # HTML buffer
        'document',           # Document content
        'initialized',        # Is initialized
        'loaded',             # Is page loaded
        'item',               # Current item
        'use_buffer',         # Use HTML buffer flag
        'name_user',          # User name
        'name_bot',           # Bot name
        'last_time_called',   # Last time called timestamp
        'cooldown',           # Cooldown for parsing chunks
        'throttling_min_chars'  # Min chars to activate cooldown
    ]

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.files_appended = []
        self.buffer = ""  # stream buffer
        self.live_buffer = ""  # live stream buffer
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
