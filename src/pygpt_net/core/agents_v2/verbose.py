#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 13:55:00                  #
# ================================================== #

from __future__ import annotations

import dataclasses
import datetime
import json
import threading
from enum import Enum
from typing import Any, Dict, Iterable, Optional


class AgentsV2VerboseLogger:
    """Best-effort console logger for the complete Agents v2 runtime flow.

    Verbose logging is intentionally independent from PyGPT's global log level.
    When enabled, it writes directly to stdout so the full orchestration trace is
    visible even when the application logger is configured to ERROR/WARNING.
    """

    _lock = threading.RLock()
    _sensitive_keys = {
        "api_key", "apikey", "api-key", "authorization", "password",
        "passwd", "secret", "access_token", "refresh_token", "token",
        "client_secret",
    }

    def __init__(self, window=None, run_id: str = ""):
        self.window = window
        self.run_id = str(run_id or "-")
        try:
            self.enabled = bool(window.core.config.get("agent.v2.verbose", False))
        except Exception:
            self.enabled = False

    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    @classmethod
    def _is_sensitive_key(cls, key: Any) -> bool:
        value = str(key or "").strip().lower()
        if value in cls._sensitive_keys:
            return True
        return any(
            marker in value
            for marker in ("api_key", "apikey", "authorization", "password", "secret", "access_token", "refresh_token")
        )

    @classmethod
    def _safe_value(cls, value: Any, depth: int = 0) -> Any:
        """Convert arbitrary runtime objects to printable JSON-safe structures.

        The verbose trace intentionally includes prompts, user/tool inputs and
        outputs, but it must not dump provider credentials if an object happens
        to expose them through a config/model field.
        """
        if depth > 8:
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, bytes):
            return f"<bytes:{len(value)}>"
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                out[name] = "<redacted>" if cls._is_sensitive_key(name) else cls._safe_value(item, depth + 1)
            return out
        if isinstance(value, (list, tuple, set)):
            return [cls._safe_value(item, depth + 1) for item in value]
        if dataclasses.is_dataclass(value):
            try:
                return cls._safe_value(dataclasses.asdict(value), depth + 1)
            except Exception:
                pass
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                return cls._safe_value(model_dump(), depth + 1)
            except Exception:
                pass
        dict_fn = getattr(value, "dict", None)
        if callable(dict_fn):
            try:
                return cls._safe_value(dict_fn(), depth + 1)
            except Exception:
                pass
        public = getattr(value, "__dict__", None)
        if isinstance(public, dict):
            data = {
                key: item for key, item in public.items()
                if not str(key).startswith("_") and not callable(item)
            }
            if data:
                return cls._safe_value(data, depth + 1)
        return str(value)

    @classmethod
    def _json(cls, value: Any) -> str:
        safe = cls._safe_value(value)
        if isinstance(safe, str):
            return safe
        try:
            return json.dumps(safe, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(safe)

    def log(self, event: str, data: Any = None, actor: str = "orchestrator"):
        if not self.enabled:
            return
        try:
            label = str(event or "EVENT").strip().upper()
            actor_name = str(actor or "orchestrator").strip()
            header = f"[Agents v2][{self._timestamp()}][run={self.run_id}][{actor_name}][{label}]"
            with self._lock:
                print(header, flush=True)
                if data is not None:
                    print(self._json(data), flush=True)
        except Exception:
            # Verbose diagnostics must never affect the agent runtime.
            pass

    def text(self, event: str, text: Any, actor: str = "orchestrator"):
        if not self.enabled:
            return
        try:
            label = str(event or "TEXT").strip().upper()
            actor_name = str(actor or "orchestrator").strip()
            header = f"[Agents v2][{self._timestamp()}][run={self.run_id}][{actor_name}][{label}]"
            with self._lock:
                print(header, flush=True)
                print(str(text or ""), flush=True)
        except Exception:
            pass

    def tool_inventory(self, tools: Iterable[Any], actor: str = "orchestrator"):
        if not self.enabled:
            return
        inventory = []
        for tool in tools or []:
            try:
                metadata = getattr(tool, "metadata", None)
                name = getattr(metadata, "name", None) or getattr(tool, "name", None) or tool.__class__.__name__
                description = getattr(metadata, "description", None) or ""
                schema = None
                get_params = getattr(metadata, "get_parameters_dict", None)
                if callable(get_params):
                    try:
                        schema = get_params()
                    except Exception:
                        schema = None
                if schema is None:
                    fn_schema = getattr(metadata, "fn_schema", None)
                    if fn_schema is not None:
                        model_schema = getattr(fn_schema, "model_json_schema", None)
                        if callable(model_schema):
                            try:
                                schema = model_schema()
                            except Exception:
                                schema = None
                inventory.append({
                    "name": name,
                    "type": tool.__class__.__name__,
                    "description": description,
                    "schema": schema,
                })
            except Exception:
                inventory.append({"type": tool.__class__.__name__, "value": str(tool)})
        self.log("TOOLS", inventory, actor=actor)

    def llm_state(self, llm: Any, actor: str = "orchestrator"):
        if not self.enabled:
            return
        data = {
            "class": llm.__class__.__name__ if llm is not None else None,
        }
        try:
            metadata = getattr(llm, "metadata", None)
            if metadata is not None:
                data["metadata"] = self._safe_value(metadata)
        except Exception:
            pass

        # Only inspect known tool-related attributes. Do not dump the whole LLM
        # object because it can contain API credentials and HTTP client state.
        for key in (
            "built_in_tools",
            "pygpt_remote_tools",
            "_pygpt_remote_tools",
            "tools",
            "tool_choice",
            "parallel_tool_calls",
            "allow_parallel_tool_calls",
        ):
            try:
                value = getattr(llm, key, None)
                if value not in (None, [], {}, ""):
                    data[key] = self._safe_value(value)
            except Exception:
                pass
        self.log("LLM / REMOTE TOOLS", data, actor=actor)
