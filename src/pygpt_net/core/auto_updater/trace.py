#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
# ================================================== #

from __future__ import annotations

import re
import threading
from datetime import datetime
from typing import Any


class AutoUpdateTrace:
    """Small console tracer controlled by Settings -> Debug."""

    PREFIX = "[AUTO-UPDATER]"
    _SECRET_PATTERNS = (
        # URL user:password@host
        (re.compile(r"(?i)(https?://[^/\s:@]+:)[^@\s/]+@"), r"\1***@"),
        # Common secret-bearing URL query parameters.
        (
            re.compile(
                r"(?i)([?&](?:access_token|token|api_key|apikey|password|passwd|secret|signature|sig|auth)=)[^&\s]+"
            ),
            r"\1***",
        ),
        # Common command-line secret arguments.
        (
            re.compile(r"(?i)(--(?:api[-_]?key|access[-_]?token|token|password|passwd|secret|auth)\s+)(\S+)"),
            r"\1***",
        ),
    )

    def __init__(self, window=None):
        self.window = window
        self._lock = threading.Lock()

    def enabled(self) -> bool:
        try:
            return bool(self.window.core.config.get("log.auto_update", False))
        except Exception:
            return False

    @classmethod
    def _sanitize(cls, value: Any) -> str:
        text = str(value)
        for pattern, replacement in cls._SECRET_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def log(self, message: Any):
        if not self.enabled():
            return
        try:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            thread = threading.current_thread()
            thread_name = thread.name or str(thread.ident or "")
            line = f"{self.PREFIX} {timestamp} [{thread_name}] {self._sanitize(message)}"
            with self._lock:
                print(line, flush=True)
            # Mirror the trace to PyGPT's Debug Logger console when available.
            # This bypasses the global log-level filter intentionally: this
            # dedicated switch is the only gate for auto-updater tracing.
            try:
                if self.window is not None and hasattr(self.window, "logger_message"):
                    self.window.logger_message.emit(line)
            except Exception:
                pass
        except Exception:
            # Debug tracing must never be able to break the updater itself.
            pass
