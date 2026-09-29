#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from pygpt_net.utils import trans


def effective_iteration_limit(value: int) -> int:
    """Translate the PyGPT 0=unlimited contract to LlamaIndex semantics."""
    return sys.maxsize if value == 0 else value


def tool_event_value(event: Any, *keys: str):
    """Return the first non-empty value found in a tool event."""
    for key in keys:
        if isinstance(event, dict):
            value = event.get(key)
        else:
            value = getattr(event, key, None)
        if value not in (None, ""):
            return value
    return None


def json_safe_tool_value(value: Any) -> Any:
    """Return a persistence-safe tool argument value."""
    if value is None:
        return {}
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return json.loads(stripped)
            except Exception:
                return value
        return ""
    try:
        # Round-trip with ``default=str`` so a provider-specific scalar or
        # Pydantic value can never make CtxItem persistence fail.
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


def json_safe_tool_result(value: Any) -> Any:
    """Return a persistence-safe tool response without changing plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return json.loads(stripped)
            except Exception:
                return value
        return ""
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


def tool_result_value(event: Any) -> Any:
    """Extract the actual ToolCallResult payload, including valid empty output."""
    for key in ("tool_output", "output", "result", "response"):
        if isinstance(event, dict):
            if key not in event:
                continue
            value = event.get(key)
        else:
            if not hasattr(event, key):
                continue
            value = getattr(event, key, None)
        if value is None:
            continue
        if isinstance(value, dict) and "content" in value:
            return value.get("content")
        content = getattr(value, "content", None)
        if content is not None:
            return content
        return value
    return ""


def supports_function_calling(llm) -> bool:
    """Return whether an LLM advertises native function calling support."""
    try:
        return bool(llm.metadata.is_function_calling_model)
    except Exception:
        return False


def short_status_text(value: str, limit: int = 72) -> str:
    """Normalize and truncate text for compact runtime status output."""
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[:max(1, limit - 3)].rstrip() + "..."


def translated_status(key: str, **kwargs) -> str:
    """Translate a runtime-generated status and safely interpolate placeholders."""
    value = trans(key)
    try:
        return value.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return value


def result_text(result: Any) -> str:
    """Extract a normalized text response from an agent result."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    response = getattr(result, "response", None)
    if response is not None:
        content = getattr(response, "content", None)
        if content:
            return str(content).strip()
        if isinstance(response, str):
            return response.strip()
    content = getattr(result, "content", None)
    if content:
        return str(content).strip()
    return str(result).strip()


def legacy_worker_context_record(value: Any) -> Optional[Dict[str, Any]]:
    """Convert the short-lived ``worker_outputs`` format to ``worker_context``."""
    if not isinstance(value, dict):
        return None
    output = value.get("output")
    if output is None:
        output = value.get("output_text")
    created_at = value.get("created_at")
    if created_at is None:
        created_at = value.get("output_created_at")
    try:
        created_at = int(created_at or 0)
    except (TypeError, ValueError):
        created_at = 0
    return {
        "id": str(value.get("id") or value.get("worker_id") or ""),
        "name": str(value.get("name") or value.get("worker_name") or ""),
        "input": str(value.get("input") or value.get("task") or ""),
        "output": str(output or ""),
        "created_at": created_at,
    }
