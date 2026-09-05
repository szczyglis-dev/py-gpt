#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import threading
from typing import Any, Dict, Optional


_lock = threading.RLock()
_requests: Dict[int, Dict[str, Any]] = {}


def register(ctx, request: Dict[str, Any]) -> None:
    """Register one in-memory Agents v2 plugin request for a private tool context."""
    if ctx is None or not isinstance(request, dict):
        return
    with _lock:
        _requests[id(ctx)] = request


def get(ctx) -> Optional[Dict[str, Any]]:
    if ctx is None:
        return None
    with _lock:
        request = _requests.get(id(ctx))
        if isinstance(request, dict) and request.get("ctx") is ctx:
            return request
        return None


def pop(ctx) -> Optional[Dict[str, Any]]:
    if ctx is None:
        return None
    with _lock:
        request = _requests.get(id(ctx))
        if isinstance(request, dict) and request.get("ctx") is ctx:
            return _requests.pop(id(ctx), None)
        return None


def discard(ctx, request: Optional[Dict[str, Any]] = None) -> None:
    if ctx is None:
        return
    with _lock:
        current = _requests.get(id(ctx))
        if current is None:
            return
        if request is None or current is request:
            _requests.pop(id(ctx), None)


def mark_pending(ctx, pending: bool = True) -> None:
    with _lock:
        request = _requests.get(id(ctx)) if ctx is not None else None
        if isinstance(request, dict) and request.get("ctx") is ctx:
            request["pending"] = bool(pending)


def is_pending(ctx) -> bool:
    with _lock:
        request = _requests.get(id(ctx)) if ctx is not None else None
        return bool(
            isinstance(request, dict)
            and request.get("ctx") is ctx
            and request.get("pending", False)
        )
