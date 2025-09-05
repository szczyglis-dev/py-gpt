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

import io
from typing import Optional

from .utils import as_int


def process_anthropic_chunk(ctx, core, state, chunk) -> Optional[str]:
    """
    Anthropic streaming events handler. Supports both full event objects and top-level delta objects.

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    state.usage_vendor = "anthropic"
    etype = str(getattr(chunk, "type", "") or "")
    response: Optional[str] = None

    # --- Top-level delta objects (when SDK yields deltas directly) ---
    if etype == "text_delta":
        txt = getattr(chunk, "text", None)
        return str(txt) if txt is not None else None

    if etype == "thinking_delta":
        return None

    if etype == "input_json_delta":
        pj = getattr(chunk, "partial_json", "") or ""
        buf = state.fn_args_buffers.get("__anthropic_last__")
        if buf is None:
            buf = io.StringIO()
            state.fn_args_buffers["__anthropic_last__"] = buf
        buf.write(pj)
        if state.tool_calls:
            state.tool_calls[-1]["function"]["arguments"] = buf.getvalue()
        return None

    if etype == "signature_delta":
        return None

    # --- Standard event flow ---
    if etype == "message_start":
        try:
            msg = getattr(chunk, "message", None)
            um = getattr(msg, "usage", None) if msg else None
            if um:
                inp = as_int(getattr(um, "input_tokens", None))
                if inp is not None:
                    state.usage_payload["in"] = inp
        except Exception:
            pass
        return None

    if etype == "content_block_start":
        try:
            cb = getattr(chunk, "content_block", None)
            if cb and getattr(cb, "type", "") == "tool_use":
                idx = getattr(chunk, "index", 0) or 0
                tid = getattr(cb, "id", "") or ""
                name = getattr(cb, "name", "") or ""
                state.tool_calls.append({
                    "id": tid,
                    "type": "function",
                    "function": {"name": name, "arguments": ""}
                })
                state.fn_args_buffers[str(idx)] = io.StringIO()
                state.fn_args_buffers["__anthropic_last__"] = state.fn_args_buffers[str(idx)]
        except Exception:
            pass

        try:
            cb = getattr(chunk, "content_block", None)
            if cb and getattr(cb, "type", "") == "web_search_tool_result":
                results = getattr(cb, "content", None) or []
                for r in results:
                    url = r.get("url") if isinstance(r, dict) else None
                    if url:
                        if ctx.urls is None:
                            ctx.urls = []
                        if url not in ctx.urls:
                            ctx.urls.append(url)
        except Exception:
            pass

        return None

    if etype == "content_block_delta":
        try:
            delta = getattr(chunk, "delta", None)
            if not delta:
                return None
            if getattr(delta, "type", "") == "text_delta":
                txt = getattr(delta, "text", None)
                if txt is not None:
                    response = str(txt)
            elif getattr(delta, "type", "") == "input_json_delta":
                idx = str(getattr(chunk, "index", 0) or 0)
                buf = state.fn_args_buffers.get(idx)
                pj = getattr(delta, "partial_json", "") or ""
                if buf is None:
                    buf = io.StringIO()
                    state.fn_args_buffers[idx] = buf
                buf.write(pj)
                state.fn_args_buffers["__anthropic_last__"] = buf
                try:
                    if state.tool_calls:
                        tc = state.tool_calls[-1]
                        tc["function"]["arguments"] = buf.getvalue()
                except Exception:
                    pass
        except Exception:
            pass
        return response

    if etype == "content_block_stop":
        try:
            idx = str(getattr(chunk, "index", 0) or 0)
            buf = state.fn_args_buffers.pop(idx, None)
            if buf is not None:
                try:
                    args_val = buf.getvalue()
                finally:
                    try:
                        buf.close()
                    except Exception:
                        pass
                if state.tool_calls:
                    state.tool_calls[-1]["function"]["arguments"] = args_val
            if state.fn_args_buffers.get("__anthropic_last__") is buf:
                state.fn_args_buffers.pop("__anthropic_last__", None)
        except Exception:
            pass
        return None

    if etype == "message_delta":
        try:
            usage = getattr(chunk, "usage", None)
            if usage:
                out_tok = as_int(getattr(usage, "output_tokens", None))
                if out_tok is not None:
                    state.usage_payload["out"] = out_tok
            delta = getattr(chunk, "delta", None)
            stop_reason = getattr(delta, "stop_reason", None) if delta else None
        except Exception:
            pass
        return None

    if etype == "message_stop":
        return None

    return None