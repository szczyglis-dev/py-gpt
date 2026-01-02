#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 02:00:00                  #
# ================================================== #

import base64
import json
from typing import Optional, Any

from .utils import capture_google_usage, collect_google_citations


def process_google_chunk(ctx, core, state, chunk) -> Optional[str]:
    """
    Google python-genai streaming chunk.

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    response_parts: list[str] = []

    if state.google_stream_ref is None:
        state.google_stream_ref = state.generator

    try:
        um = getattr(chunk, "usage_metadata", None)
        if um:
            capture_google_usage(state, um)
    except Exception:
        pass

    try:
        t = getattr(chunk, "text", None)
        if t:
            response_parts.append(t)
    except Exception:
        pass

    fc_list = []
    try:
        fc_list = getattr(chunk, "function_calls", None) or []
    except Exception:
        fc_list = []

    new_calls = []

    def _to_plain_dict(obj: Any):
        """Best-effort conversion of SDK objects to plain dict/list."""
        try:
            if hasattr(obj, "to_json_dict"):
                return obj.to_json_dict()
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
        except Exception:
            pass
        if isinstance(obj, dict):
            return {k: _to_plain_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_plain_dict(x) for x in obj]
        return obj

    if fc_list:
        for fc in fc_list:
            name = getattr(fc, "name", "") or ""
            args_obj = getattr(fc, "args", {}) or {}
            args_dict = _to_plain_dict(args_obj) or {}
            new_calls.append({
                "id": getattr(fc, "id", "") or "",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args_dict, ensure_ascii=False),
                }
            })
    else:
        try:
            cands = getattr(chunk, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    fn = getattr(p, "function_call", None)
                    if not fn:
                        continue
                    name = getattr(fn, "name", "") or ""
                    args_obj = getattr(fn, "args", {}) or {}
                    args_dict = _to_plain_dict(args_obj) or {}
                    new_calls.append({
                        "id": getattr(fn, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args_dict, ensure_ascii=False),
                        }
                    })
        except Exception:
            pass

    new_calls, has_calls = core.api.google.computer.handle_stream_chunk(ctx, chunk, new_calls)
    if has_calls:
        ctx.extra["function_response_required"] = True  # required for automatic with-screenshot response
        ctx.extra["function_response_source"] = "ctx.tool_calls"
        ctx.extra["function_response_reason"] = "computer_use"
        state.force_func_call = True

    if new_calls:
        seen = {(tc["function"]["name"], tc["function"]["arguments"]) for tc in state.tool_calls}
        for tc in new_calls:
            key = (tc["function"]["name"], tc["function"]["arguments"])
            if key not in seen:
                state.tool_calls.append(tc)
                seen.add(key)

    try:
        cands = getattr(chunk, "candidates", None) or []
        for cand in cands:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []

            for p in parts:
                ex = getattr(p, "executable_code", None)
                if ex:
                    lang = (getattr(ex, "language", None) or "python").strip() or "python"
                    code_txt = (
                        getattr(ex, "code", None) or
                        getattr(ex, "program", None) or
                        getattr(ex, "source", None) or
                        ""
                    )
                    if code_txt is None:
                        code_txt = ""
                    if not state.is_code:
                        response_parts.append(f"\n\n**Code interpreter**\n```{lang.lower()}\n{code_txt}")
                        state.is_code = True
                    else:
                        response_parts.append(str(code_txt))

                cer = getattr(p, "code_execution_result", None)
                if cer:
                    if state.is_code:
                        response_parts.append("\n\n```\n-----------\n")
                        state.is_code = False

                blob = getattr(p, "inline_data", None)
                if blob:
                    mime = (getattr(blob, "mime_type", "") or "").lower()
                    if mime.startswith("image/"):
                        data = getattr(blob, "data", None)
                        if data:
                            if isinstance(data, (bytes, bytearray)):
                                img_bytes = bytes(data)
                            else:
                                img_bytes = base64.b64decode(data)
                            save_path = core.image.gen_unique_path(ctx)
                            with open(save_path, "wb") as f:
                                f.write(img_bytes)
                            if not isinstance(ctx.images, list):
                                ctx.images = []
                            ctx.images.append(save_path)
                            state.image_paths.append(save_path)
                            state.has_google_inline_image = True

                fdata = getattr(p, "file_data", None)
                if fdata:
                    uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                    mime = (getattr(fdata, "mime_type", "") or "").lower()
                    if uri and mime.startswith("image/") and (uri.startswith("http://") or uri.startswith("https://")):
                        if ctx.urls is None:
                            ctx.urls = []
                        ctx.urls.append(uri)

        collect_google_citations(ctx, state, chunk)

    except Exception:
        pass

    return "".join(response_parts) if response_parts else None