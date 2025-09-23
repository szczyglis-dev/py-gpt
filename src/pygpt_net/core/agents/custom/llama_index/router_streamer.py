#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
import json
import re
from typing import Optional


class DelayedRouterStreamerLI:
    """Collect raw JSON stream (no UI)."""
    def __init__(self):
        self._raw = ""
    def reset(self):
        self._raw = ""
    def handle_delta(self, delta: str):
        self._raw += delta or ""
    @property
    def buffer(self) -> str:
        return self._raw


class RealtimeRouterStreamerLI:
    """
    Stream only JSON 'content' string incrementally.
    handle_delta(delta) -> returns decoded content suffix to emit (may be '').
    """
    CONTENT_PATTERN = re.compile(r'"content"\s*:\s*"')

    def __init__(self):
        self._raw = ""
        self._content_started = False
        self._content_closed = False
        self._content_start_idx = -1
        self._content_raw = ""
        self._content_decoded = ""

    def reset(self):
        self._raw = ""
        self._content_started = False
        self._content_closed = False
        self._content_start_idx = -1
        self._content_raw = ""
        self._content_decoded = ""

    def handle_delta(self, delta: str) -> str:
        if not delta:
            return ""
        self._raw += delta
        if not self._content_started:
            m = self.CONTENT_PATTERN.search(self._raw)
            if m:
                self._content_started = True
                self._content_start_idx = m.end()
            else:
                return ""
        if self._content_started and not self._content_closed:
            return self._process()
        return ""

    def _process(self) -> str:
        sub = self._raw[self._content_start_idx:]
        close_idx = self._find_unescaped_quote(sub)
        if close_idx is not None:
            portion = sub[:close_idx]
            self._content_closed = True
        else:
            portion = sub
        new_raw_piece = portion[len(self._content_raw):]
        if not new_raw_piece:
            return ""
        self._content_raw += new_raw_piece
        try:
            decoded_full = json.loads(f'"{self._content_raw}"')
            new_suffix = decoded_full[len(self._content_decoded):]
            self._content_decoded = decoded_full
            return new_suffix
        except Exception:
            return ""

    @staticmethod
    def _find_unescaped_quote(s: str) -> Optional[int]:
        i = 0
        while i < len(s):
            if s[i] == '"':
                j = i - 1
                bs = 0
                while j >= 0 and s[j] == '\\':
                    bs += 1
                    j -= 1
                if bs % 2 == 0:
                    return i
            i += 1
        return None

    @property
    def buffer(self) -> str:
        return self._raw