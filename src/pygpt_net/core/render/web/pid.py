#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.12 19:00:00                  #
# ================================================== #

import io
from pygpt_net.utils import trans


class PidData:

    def __init__(self, pid, meta=None):
        """Pid Data"""
        self.pid = pid
        self.meta = meta
        self.images_appended = []
        self.urls_appended = []
        self.files_appended = []
        self._buffer = io.StringIO()
        self._live_buffer = io.StringIO()
        self._html = io.StringIO()
        self._document = io.StringIO()
        self.is_cmd = False
        self.initialized = False
        self.loaded = False
        self.item = None
        self.use_buffer = False
        self.name_user = trans("chat.name.user")
        self.name_bot = trans("chat.name.bot")
        self.last_time_called = 0
        self.cooldown = 1 / 6
        self.throttling_min_chars = 5000

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

    @property
    def live_buffer(self) -> str:
        return self._live_buffer.getvalue()

    @live_buffer.setter
    def live_buffer(self, value: str):
        self._live_buffer.seek(0)
        self._live_buffer.truncate(0)
        if value:
            self._live_buffer.write(value)

    def append_live_buffer(self, text: str):
        self._live_buffer.write(text)

    @property
    def html(self) -> str:
        return self._html.getvalue()

    @html.setter
    def html(self, value: str):
        self._html.seek(0)
        self._html.truncate(0)
        if value:
            self._html.write(value)

    def append_html(self, text: str):
        self._html.write(text)

    @property
    def document(self) -> str:
        return self._document.getvalue()

    @document.setter
    def document(self, value: str):
        self._document.seek(0)
        self._document.truncate(0)
        if value:
            self._document.write(value)

    def append_document(self, text: str):
        self._document.write(text)

    def clear(self, all: bool = False):
        """
        Clear buffers and other data

        :param all: If True, clear all data, otherwise only buffers
        """
        for buf in (self._html, self._document, self._buffer, self._live_buffer):
            buf.seek(0)
            buf.truncate(0)

        if all:
            self.item = None
            self.images_appended.clear()
            self.urls_appended.clear()
            self.files_appended.clear()