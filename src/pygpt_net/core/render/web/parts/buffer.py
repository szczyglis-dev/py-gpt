#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Allocation-friendly text buffer shared by streaming channels."""

from dataclasses import dataclass, field
from io import StringIO

@dataclass(slots=True)
class AppendBuffer:
    """Small, allocation-friendly buffer for throttled appends."""
    _buf: StringIO = field(default_factory=StringIO, repr=False)
    _size: int = 0

    # ========================================
    # Buffer lifecycle
    # ========================================

    def append(self, s: str) -> None:
        if not s:
            return
        self._buf.write(s)
        self._size += len(s)

    def clear(self) -> None:
        """Clear content and drop buffer capacity."""
        old = self._buf
        self._buf = StringIO()
        self._size = 0
        try:
            old.close()
        except Exception:
            pass

    # ========================================
    # Buffer readout
    # ========================================

    def is_empty(self) -> bool:
        return self._size == 0

    def get_and_clear(self) -> str:
        """Return content and replace underlying buffer to release memory eagerly."""
        if self._size == 0:
            return ""
        data = self._buf.getvalue()
        old = self._buf
        self._buf = StringIO()
        self._size = 0
        try:
            old.close()
        except Exception:
            pass
        return data
