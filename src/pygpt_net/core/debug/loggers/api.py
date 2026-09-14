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

from collections import Counter
from typing import Any, Dict, Optional

from .base import BaseDebugLogger


class ApiDebugLogger(BaseDebugLogger):
    """Readable opt-in logging for provider/LlamaIndex API input and output."""

    INPUT_KEY = "log.api.input"
    OUTPUT_KEY = "log.api.output"

    def log_input(
            self,
            type: str,
            provider: str = "",
            args: Any = None,
            kwargs: Optional[Dict[str, Any]] = None,
            input: Any = None,
            history: Any = None,
            extra: Any = None,
            path: Any = None,
            model: Any = None,
    ):
        if not self.enabled(self.INPUT_KEY):
            return
        payload = {
            "type": str(type or "api"),
            "provider": str(provider or ""),
        }
        if model is not None:
            payload["model"] = self.safe_value(model, key="model")
        if path is not None:
            payload["path"] = self.safe_value(path, key="path")
        if args is not None:
            payload["args"] = self.safe_value(args, key="args")
        if kwargs is not None:
            payload["kwargs"] = self.safe_value(kwargs, key="kwargs")
        if input is not None:
            payload["input"] = self.safe_value(input, key="input")
        if history is not None:
            payload["history"] = self.safe_value(history, key="history")
        if extra is not None:
            payload["extra"] = self.safe_value(extra, key="extra")
        self.emit("API INPUT", payload)

    @staticmethod
    def _block_type(item: Any) -> str:
        if item is None:
            return "None"
        if isinstance(item, dict):
            return str(item.get("type") or item.get("role") or "dict")
        return str(getattr(item, "type", None) or getattr(item, "role", None) or type(item).__name__)

    def _summary(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return {
                "type": "str",
                "length": len(value),
                "preview": value[:1000],
            }
        if isinstance(value, (list, tuple)):
            types = Counter(self._block_type(item) for item in value)
            return {
                "type": type(value).__name__,
                "count": len(value),
                "item_types": dict(types),
                "preview": self.safe_value(list(value[:5]) if isinstance(value, list) else list(value)[:5]),
            }
        if isinstance(value, dict):
            summary = {
                "type": "dict",
                "keys": list(value.keys()),
            }
            for key in ("id", "model", "status", "stop_reason", "finish_reason", "usage", "citations", "output", "content", "choices"):
                if key in value:
                    child = value[key]
                    if key in ("output", "content", "choices"):
                        summary[key] = self._summary(child)
                    else:
                        summary[key] = self.safe_value(child, key=key)
            return summary

        data = self.safe_value(value)
        if isinstance(data, dict):
            summary = {
                "type": data.get("__type__", f"{type(value).__module__}.{type(value).__name__}"),
                "keys": [k for k in data.keys() if k != "__type__"],
            }
            for key in ("id", "model", "status", "stop_reason", "finish_reason", "usage", "output", "content", "choices"):
                if key in data:
                    summary[key] = self._summary(data[key]) if key in ("output", "content", "choices") else data[key]
            return summary
        return data

    def log_output(
            self,
            type: str,
            provider: str = "",
            output: Any = None,
            chunks: Optional[int] = None,
            chunk_types: Optional[Dict[str, int]] = None,
            tool_calls: Any = None,
            usage: Any = None,
            error: Any = None,
            model: Any = None,
            extra: Any = None,
    ):
        if not self.enabled(self.OUTPUT_KEY):
            return
        payload = {
            "type": str(type or "api"),
            "provider": str(provider or ""),
        }
        if model is not None:
            payload["model"] = self.safe_value(model, key="model")
        if chunks is not None:
            payload["chunks"] = int(chunks)
        if chunk_types:
            payload["chunk_types"] = dict(chunk_types)
        payload["summary"] = self._summary(output)
        if tool_calls:
            payload["tool_calls"] = self.safe_value(tool_calls, key="tool_calls")
        if usage:
            payload["usage"] = self.safe_value(usage, key="usage")
        if error is not None:
            payload["error"] = self.safe_value(error, key="error")
        if extra is not None:
            payload["extra"] = self.safe_value(extra, key="extra")
        self.emit("API OUTPUT", payload)
