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

class PidData:

    __slots__ = [
        'pid',                # Process ID
        'meta',               # CtxMeta instance
        'images_appended',    # Images appended to the process
        'urls_appended',      # URLs appended to ctx
        'files_appended',     # Files appended to ctx
        'buffer',             # Buffer for data
        'is_cmd'              # Flag indicating if it's a command
    ]

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.files_appended = []
        self.buffer = ""
        self.is_cmd = False
