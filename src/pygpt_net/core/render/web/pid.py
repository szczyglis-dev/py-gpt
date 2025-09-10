#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.07 05:00:00                  #
# ================================================== #

import io
from dataclasses import dataclass, field
from typing import Any, Optional

from pygpt_net.utils import trans


@dataclass(slots=True)
class PidData:
    """Pid Data"""
    # Required/primary data
    pid: Any
    meta: Optional[Any] = None

    # Collections
    images_appended: list = field(default_factory=list)
    urls_appended: list = field(default_factory=list)
    files_appended: list = field(default_factory=list)

    # Internal buffers (excluded from repr to avoid large dumps)
    _buffer: io.StringIO = field(default_factory=io.StringIO, repr=False)
    _live_buffer: io.StringIO = field(default_factory=io.StringIO, repr=False)
    _html: io.StringIO = field(default_factory=io.StringIO, repr=False)
    _document: io.StringIO = field(default_factory=io.StringIO, repr=False)
    _fence_tail: str = field(default="", repr=False)
    _fence_open: bool = field(default=False, repr=False)
    _fence_char: str = field(default="", repr=False)

    # Flags/state
    is_cmd: bool = False
    initialized: bool = False
    loaded: bool = False
    item: Optional[Any] = None
    use_buffer: bool = False

    # Names
    name_user: str = field(default_factory=lambda: trans("chat.name.user"))
    name_bot: str = field(default_factory=lambda: trans("chat.name.bot"))

    # Throttling / timing
    last_time_called: float = 0.0
    cooldown: float = 1 / 6
    throttling_min_chars: int = 5000

    # Misc
    header: Optional[Any] = None

    @property
    def buffer(self) -> str:
        return self._buffer.getvalue()

    @buffer.setter
    def buffer(self, value: str):
        if value is None or value == "":
            self._buffer.close()
            self._buffer = io.StringIO()
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
        if value is None or value == "":
            self._live_buffer.close()
            self._live_buffer = io.StringIO()
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
        if value is None or value == "":
            self._html.close()
            self._html = io.StringIO()
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
        if value is None or value == "":
            self._document.close()
            self._document = io.StringIO()
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
        for name in ("_buffer", "_live_buffer", "_html", "_document"):
            try:
                getattr(self, name).close()
            except Exception:
                pass
            setattr(self, name, io.StringIO())

        if all:
            self.item = None
            self.images_appended.clear()
            self.urls_appended.clear()
            self.files_appended.clear()