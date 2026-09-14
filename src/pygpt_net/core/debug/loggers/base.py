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

import json
import threading
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict


class BaseDebugLogger:
    """Common formatting/sanitizing helpers for opt-in terminal debug logs."""

    _SECRET_KEYS = {
        "api_key", "apikey", "access_token", "auth_token", "authorization",
        "bearer", "client_secret", "password", "secret", "token",
        "management_api_key", "organization_key",
    }
    _SECRET_SUFFIXES = (
        "_api_key", "_access_token", "_auth_token", "_client_secret",
        "_password", "_secret", "_secret_key", "_private_key", "_token",
    )
    _BINARY_KEYS = ("image", "audio", "file", "bytes", "base64", "b64_json")

    def __init__(self, window=None):
        self.window = window
        self._lock = threading.RLock()

    def enabled(self, key: str) -> bool:
        try:
            return bool(self.window and self.window.core.config.get(key, False))
        except Exception:
            return False

    @classmethod
    def _is_secret_key(cls, key: Any) -> bool:
        value = str(key or "").strip().lower().replace("-", "_")
        if value in cls._SECRET_KEYS:
            return True
        return any(value.endswith(suffix) for suffix in cls._SECRET_SUFFIXES)

    @classmethod
    def _looks_binary_key(cls, key: Any) -> bool:
        value = str(key or "").lower()
        return any(marker in value for marker in cls._BINARY_KEYS)

    @staticmethod
    def _binary_summary(value: Any) -> str:
        if isinstance(value, (bytes, bytearray, memoryview)):
            return f"<{type(value).__name__}: {len(value)} bytes>"
        if isinstance(value, str):
            return f"<binary/text payload: {len(value)} chars>"
        return f"<{type(value).__name__}>"

    @classmethod
    def safe_value(cls, value: Any, key: Any = None, depth: int = 0) -> Any:
        """Convert arbitrary SDK/LlamaIndex objects into terminal-safe JSON values."""
        if cls._is_secret_key(key):
            if value in (None, ""):
                return value
            return "***MASKED***"

        if cls._looks_binary_key(key) and isinstance(value, (bytes, bytearray, memoryview)):
            return cls._binary_summary(value)

        if value is None or isinstance(value, (bool, int, float, str)):
            if isinstance(value, str) and len(value) > 200_000:
                return value[:200_000] + f"\n<... truncated {len(value) - 200_000} chars>"
            return value

        if isinstance(value, (bytes, bytearray, memoryview)):
            return cls._binary_summary(value)

        if isinstance(value, Path):
            return str(value)

        if depth >= 12:
            return f"<{type(value).__module__}.{type(value).__name__}>"

        if isinstance(value, dict):
            return {
                str(k): cls.safe_value(v, key=k, depth=depth + 1)
                for k, v in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [cls.safe_value(v, depth=depth + 1) for v in value]

        # Prefer explicit serializers over dataclasses.asdict(). Bridge/SDK
        # objects often expose a deliberately bounded representation while
        # asdict() may recursively traverse large runtime graphs.
        for attr in ("model_dump", "to_dict", "dict"):
            fn = getattr(value, attr, None)
            if callable(fn):
                try:
                    return cls.safe_value(fn(), depth=depth + 1)
                except Exception:
                    pass

        if is_dataclass(value):
            try:
                return cls.safe_value(asdict(value), depth=depth + 1)
            except Exception:
                pass

        try:
            data = vars(value)
            if data:
                return {
                    "__type__": f"{type(value).__module__}.{type(value).__name__}",
                    **cls.safe_value(data, depth=depth + 1),
                }
        except Exception:
            pass

        try:
            text = str(value)
        except Exception:
            text = repr(value)
        if len(text) > 20_000:
            text = text[:20_000] + f"<... truncated {len(text) - 20_000} chars>"
        return f"<{type(value).__module__}.{type(value).__name__}: {text}>"

    @staticmethod
    def _json(data: Any) -> str:
        try:
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(data)

    def emit(self, title: str, payload: Dict[str, Any]):
        with self._lock:
            print(f"\n{'=' * 18} {title} {'=' * 18}")
            print(self._json(payload))
            print("=" * (38 + len(title)))
