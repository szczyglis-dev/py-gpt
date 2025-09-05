#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 00:00:00                  #
# ================================================== #

from typing import Optional


def process_xai_sdk_chunk(ctx, core, state, item) -> Optional[str]:
    """
    xAI SDK native streaming chunk.

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param item: Incoming streaming chunk (tuple of (response, chunk))
    :return: Extracted text delta or None
    """
    try:
        response, chunk = item
    except Exception:
        return None

    state.xai_last_response = response

    try:
        if hasattr(chunk, "content") and chunk.content is not None:
            return str(chunk.content)
        if isinstance(chunk, str):
            return chunk
    except Exception:
        pass
    return None


def xai_extract_tool_calls(response) -> list[dict]:
    """
    Extract tool calls from xAI SDK final response (proto).

    :param response: xAI final response object
    :return: List of tool calls in normalized dict format
    """
    out: list[dict] = []
    try:
        proto = getattr(response, "proto", None)
        if not proto:
            return out
        choices = getattr(proto, "choices", None) or []
        if not choices:
            return out
        msg = getattr(choices[0], "message", None)
        if not msg:
            return out
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            try:
                name = getattr(getattr(tc, "function", None), "name", "") or ""
                args = getattr(getattr(tc, "function", None), "arguments", "") or "{}"
                out.append({
                    "id": getattr(tc, "id", "") or "",
                    "type": "function",
                    "function": {"name": name, "arguments": args},
                })
            except Exception:
                continue
    except Exception:
        pass
    return out


def xai_extract_citations(response) -> list[str]:
    """
    Extract citations (URLs) from xAI final response if present.

    :param response: xAI final response object
    :return: List of citation URLs
    """
    urls: list[str] = []
    try:
        cites = getattr(response, "citations", None)
        if isinstance(cites, (list, tuple)):
            for u in cites:
                if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                    if u not in urls:
                        urls.append(u)
    except Exception:
        pass
    try:
        proto = getattr(response, "proto", None)
        if proto:
            proto_cites = getattr(proto, "citations", None) or []
            for u in proto_cites:
                if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                    if u not in urls:
                        urls.append(u)
    except Exception:
        pass
    return urls


def xai_extract_usage(response) -> dict:
    """
    Extract usage from xAI final response via proto. Return {'in','out','reasoning','total'}.

    :param response: xAI final response object
    :return: Usage dict
    """
    try:
        proto = getattr(response, "proto", None)
        usage = getattr(proto, "usage", None) if proto else None
        if not usage:
            return {}

        def _as_int(v):
            try:
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return 0

        p = _as_int(getattr(usage, "prompt_tokens", 0) or 0)
        c = _as_int(getattr(usage, "completion_tokens", 0) or 0)
        t = _as_int(getattr(usage, "total_tokens", (p + c)) or (p + c))
        out_total = max(0, t - p) if t else c
        return {"in": p, "out": out_total, "reasoning": 0, "total": t}
    except Exception:
        return {}