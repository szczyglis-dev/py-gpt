#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import io
from dataclasses import dataclass, field


@dataclass(slots=True)
class PidData:

    pid: object = None
    meta: object = None
    images_appended: list = field(default_factory=list)
    urls_appended: list = field(default_factory=list)
    files_appended: list = field(default_factory=list)
    _buffer: io.StringIO = field(default_factory=io.StringIO)
    is_cmd: bool = False
    loaded: bool = False

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.files_appended = []
        self._buffer = io.StringIO()
        self.is_cmd = False
        self.loaded = False

    @property
    def buffer(self) -> str:
        return self._buffer.getvalue()

    @buffer.setter
    def buffer(self, value: str):
        self._buffer.seek(0)
        self._buffer.truncate(0)
        if value:
            self._buffer.write(value)

    def append_buffer(self, text: str):
        self._buffer.write(text)