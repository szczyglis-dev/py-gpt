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

import base64
import io
import json
from typing import Optional, Any

from .utils import capture_openai_usage


def process_api_chat(ctx, state, chunk) -> Optional[str]:
    """
    OpenAI-compatible Chat Completions stream delta (robust to dict/object tool_calls).

    :param ctx: Chat context
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    response = None
    delta = chunk.choices[0].delta if getattr(chunk, "choices", None) else None

    # Capture citations (top-level) if present
    try:
        cits = getattr(chunk, "citations", None)
        if cits:
            state.citations = cits
            ctx.urls = cits
    except Exception:
        pass

    # Capture usage (top-level) if present
    try:
        u = getattr(chunk, "usage", None)
        if u:
            capture_openai_usage(state, u)
    except Exception:
        pass

    # Text delta
    if delta and getattr(delta, "content", None) is not None:
        response = delta.content

    # Tool calls (support OpenAI object or xAI dict)
    if delta and getattr(delta, "tool_calls", None):
        state.force_func_call = True
        for tool_chunk in delta.tool_calls:
            # Normalize fields
            if isinstance(tool_chunk, dict):
                idx = tool_chunk.get("index")
                id_val = tool_chunk.get("id")
                fn = tool_chunk.get("function") or {}
                name_part = fn.get("name")
                args_part = fn.get("arguments")
            else:
                idx = getattr(tool_chunk, "index", None)
                id_val = getattr(tool_chunk, "id", None)
                fn_obj = getattr(tool_chunk, "function", None)
                name_part = getattr(fn_obj, "name", None) if fn_obj else None
                args_part = getattr(fn_obj, "arguments", None) if fn_obj else None

            # Default index when missing
            if idx is None or not isinstance(idx, int):
                idx = len(state.tool_calls)

            # Ensure list length
            while len(state.tool_calls) <= idx:
                state.tool_calls.append({
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""}
                })
            tool_call = state.tool_calls[idx]

            # Append id fragment (if streamed)
            if id_val:
                frag = str(id_val)
                if not tool_call["id"]:
                    tool_call["id"] = frag
                else:
                    if not tool_call["id"].endswith(frag):
                        tool_call["id"] += frag

            # Append name fragment
            if name_part:
                frag = str(name_part)
                if not tool_call["function"]["name"]:
                    tool_call["function"]["name"] = frag
                else:
                    if not tool_call["function"]["name"].endswith(frag):
                        tool_call["function"]["name"] += frag

            # Append arguments fragment (string or JSON)
            if args_part is not None:
                if isinstance(args_part, (dict, list)):
                    frag = json.dumps(args_part, ensure_ascii=False)
                else:
                    frag = str(args_part)
                tool_call["function"]["arguments"] += frag

    return response


def process_api_chat_responses(ctx, core, state, chunk, etype: Optional[str]) -> Optional[str]:
    """
    OpenAI Responses API stream events.

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :param etype: Event type
    :return: Extracted text delta or None
    """
    response = None

    if etype == "response.completed":
        # usage on final response
        try:
            u = getattr(chunk.response, "usage", None)
            if u:
                capture_openai_usage(state, u)
        except Exception:
            pass

        for item in chunk.response.output:
            if item.type == "mcp_list_tools":
                core.api.openai.responses.mcp_tools = item.tools
            elif item.type == "mcp_call":
                call = {
                    "id": item.id,
                    "type": "mcp_call",
                    "approval_request_id": item.approval_request_id,
                    "arguments": item.arguments,
                    "error": item.error,
                    "name": item.name,
                    "output": item.output,
                    "server_label": item.server_label,
                }
                state.tool_calls.append({
                    "id": item.id,
                    "call_id": "",
                    "type": "function",
                    "function": {"name": item.name, "arguments": item.arguments}
                })
                ctx.extra["mcp_call"] = call
                core.ctx.update_item(ctx)
            elif item.type == "mcp_approval_request":
                call = {
                    "id": item.id,
                    "type": "mcp_call",
                    "arguments": item.arguments,
                    "name": item.name,
                    "server_label": item.server_label,
                }
                ctx.extra["mcp_approval_request"] = call
                core.ctx.update_item(ctx)

    elif etype == "response.output_text.delta":
        response = chunk.delta

    elif etype == "response.output_item.added" and chunk.item.type == "function_call":
        state.tool_calls.append({
            "id": chunk.item.id,
            "call_id": chunk.item.call_id,
            "type": "function",
            "function": {"name": chunk.item.name, "arguments": ""}
        })
        state.fn_args_buffers[chunk.item.id] = io.StringIO()

    elif etype == "response.function_call_arguments.delta":
        buf = state.fn_args_buffers.get(chunk.item_id)
        if buf is not None:
            buf.write(chunk.delta)

    elif etype == "response.function_call_arguments.done":
        buf = state.fn_args_buffers.pop(chunk.item_id, None)
        if buf is not None:
            try:
                args_val = buf.getvalue()
            finally:
                buf.close()
            for tc in state.tool_calls:
                if tc["id"] == chunk.item_id:
                    tc["function"]["arguments"] = args_val
                    break

    elif etype == "response.output_text.annotation.added":
        ann = chunk.annotation
        if ann['type'] == "url_citation":
            if state.citations is None:
                state.citations = []
            url_citation = ann['url']
            state.citations.append(url_citation)
            ctx.urls = state.citations
        elif ann['type'] == "container_file_citation":
            state.files.append({
                "container_id": ann['container_id'],
                "file_id": ann['file_id'],
            })

    elif etype == "response.reasoning_summary_text.delta":
        response = chunk.delta

    elif etype == "response.output_item.done":
        tool_calls, has_calls = core.api.openai.computer.handle_stream_chunk(ctx, chunk, state.tool_calls)
        state.tool_calls = tool_calls
        if has_calls:
            state.force_func_call = True

    elif etype == "response.code_interpreter_call_code.delta":
        if not state.is_code:
            response = "\n\n**Code interpreter**\n```python\n" + chunk.delta
            state.is_code = True
        else:
            response = chunk.delta

    elif etype == "response.code_interpreter_call_code.done":
        response = "\n\n```\n-----------\n"

    elif etype == "response.image_generation_call.partial_image":
        image_base64 = chunk.partial_image_b64
        image_bytes = base64.b64decode(image_base64)
        if state.img_path:
            with open(state.img_path, "wb") as f:
                f.write(image_bytes)
        del image_bytes
        state.is_image = True

    elif etype == "response.created":
        ctx.msg_id = str(chunk.response.id)
        core.ctx.update_item(ctx)

    elif etype in {"response.done", "response.failed", "error"}:
        pass

    return response


def process_api_completion(chunk) -> Optional[str]:
    """
    OpenAI Completions stream text delta.

    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    if getattr(chunk, "choices", None):
        choice0 = chunk.choices[0]
        if getattr(choice0, "text", None) is not None:
            return choice0.text
    return None