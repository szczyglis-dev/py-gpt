#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 10:30:00                  #
# ================================================== #

from __future__ import annotations

from collections import deque
from typing import Any

from .base import BaseDebugLogger


class ToolDebugLogger(BaseDebugLogger):
    """Common tool-call and tool-result terminal logger."""

    KEY = "log.tools"
    _CACHE_LIMIT = 2000

    def __init__(self, window=None):
        super().__init__(window)
        self._seen_calls = set()
        self._seen_results = set()
        self._call_order = deque()
        self._result_order = deque()

    def _is_duplicate(self, kind: str, call_id: Any, name: str) -> bool:
        if call_id in (None, ""):
            return False
        key = (str(call_id), str(name or ""))
        seen = self._seen_calls if kind == "call" else self._seen_results
        order = self._call_order if kind == "call" else self._result_order
        with self._lock:
            if key in seen:
                return True
            seen.add(key)
            order.append(key)
            while len(order) > self._CACHE_LIMIT:
                seen.discard(order.popleft())
        return False

    def log_call(
            self,
            name: str = "",
            params: Any = None,
            call_id: Any = None,
            provider: str = "",
            actor: str = "",
            raw: Any = None,
            extra: Any = None,
    ):
        if not self.enabled(self.KEY):
            return
        if self._is_duplicate("call", call_id, name):
            return
        payload = {
            "event": "call",
            "name": str(name or ""),
            "call_id": None if call_id in (None, "") else str(call_id),
            "provider": str(provider or ""),
            "actor": str(actor or ""),
            "params": self.safe_value(params, key="params"),
        }
        if raw is not None:
            payload["raw"] = self.safe_value(raw, key="raw")
        if extra is not None:
            payload["extra"] = self.safe_value(extra, key="extra")
        self.emit("TOOL CALL", payload)

    def log_result(
            self,
            name: str = "",
            response: Any = None,
            call_id: Any = None,
            provider: str = "",
            actor: str = "",
            raw: Any = None,
            error: Any = None,
            extra: Any = None,
    ):
        if not self.enabled(self.KEY):
            return
        if self._is_duplicate("result", call_id, name):
            return
        payload = {
            "event": "result",
            "name": str(name or ""),
            "call_id": None if call_id in (None, "") else str(call_id),
            "provider": str(provider or ""),
            "actor": str(actor or ""),
            "response": self.safe_value(response, key="response"),
        }
        if raw is not None:
            payload["raw"] = self.safe_value(raw, key="raw")
        if error is not None:
            payload["error"] = self.safe_value(error, key="error")
        if extra is not None:
            payload["extra"] = self.safe_value(extra, key="extra")
        self.emit("TOOL RESULT", payload)
