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

import io

class PidData:

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.files_appended = []
        self._buffer = io.StringIO()
        self.is_cmd = False

    @property
    def buffer(self) -> str:
        return self._buffer.getvalue()

    @buffer.setter
    def buffer(self, value: str):
        self._buffer = io.StringIO()
        if value:
            self._buffer.write(value)

    def append_buffer(self, text: str):
        self._buffer.write(text)