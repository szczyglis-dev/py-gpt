#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import re
from typing import Optional, Any

def sanitize_name(name: str) -> str:
    """
    Sanitize name

    :param name: name
    :return: sanitized name
    """
    if name is None:
        return ""
    # allowed characters: a-z, A-Z, 0-9, _, and -
    name = name.strip().lower()
    sanitized_name = re.sub(r'[^a-z0-9_-]', '_', name)
    return sanitized_name[:64]  # limit to 64 characters


def capture_openai_usage(state, u_obj: Any):
    """
    Extract usage for OpenAI/xAI-compatible chunks.

    :param state: Chat state
    :param u_obj: Usage object/dict
    """
    if not u_obj:
        return
    state.usage_vendor = "openai"
    in_tok = as_int(safe_get(u_obj, "input_tokens")) or as_int(safe_get(u_obj, "prompt_tokens"))
    out_tok = as_int(safe_get(u_obj, "output_tokens")) or as_int(safe_get(u_obj, "completion_tokens"))
    total = as_int(safe_get(u_obj, "total_tokens"))
    reasoning = (
        as_int(safe_get(u_obj, "output_tokens_details.reasoning_tokens")) or
        as_int(safe_get(u_obj, "completion_tokens_details.reasoning_tokens")) or
        as_int(safe_get(u_obj, "reasoning_tokens")) or
        0
    )
    out_with_reason = (out_tok or 0) + (reasoning or 0)
    state.usage_payload = {"in": in_tok, "out": out_with_reason, "reasoning": reasoning or 0, "total": total}

def safe_get(obj: Any, path: str) -> Any:
    """
    Dot-path getter for dicts and objects.

    :param obj: Source object or dict
    :param path: Dot-separated path, e.g. 'a.b.0.c'
    :return: Value at path or None
    """
    cur = obj
    for seg in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            if seg.isdigit() and isinstance(cur, (list, tuple)):
                idx = int(seg)
                if 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            else:
                cur = getattr(cur, seg, None)
    return cur


def as_int(val: Any) -> Optional[int]:
    """
    Coerce to int if possible, else None.

    :param val: Input value
    :return: int or None
    """
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None