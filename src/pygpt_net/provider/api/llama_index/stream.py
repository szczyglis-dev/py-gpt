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

from typing import Optional


def process_llama_chat(state, chunk) -> Optional[str]:
    """
    Llama chat streaming delta with optional tool call extraction.

    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    response = None
    if getattr(chunk, "delta", None) is not None:
        response = str(chunk.delta)

    tool_chunks = getattr(getattr(chunk, "message", None), "additional_kwargs", {}).get("tool_calls", [])
    if tool_chunks:
        for tool_chunk in tool_chunks:
            id_val = getattr(tool_chunk, "call_id", None) or getattr(tool_chunk, "id", None)
            name = getattr(tool_chunk, "name", None) or getattr(getattr(tool_chunk, "function", None), "name", None)
            args = getattr(tool_chunk, "arguments", None)
            if args is None:
                f = getattr(tool_chunk, "function", None)
                args = getattr(f, "arguments", None) if f else None
            if id_val:
                if not args:
                    args = "{}"
                tool_call = {
                    "id": id_val,
                    "type": "function",
                    "function": {"name": name, "arguments": args}
                }
                state.tool_calls.clear()
                state.tool_calls.append(tool_call)

    return response