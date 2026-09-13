#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.13 19:42:00                  #
# ================================================== #

from typing import Any, Dict, List, Optional


def _get(obj: Any, key: str, default=None):
    """Read a field from either a dict-like or object-like value."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalize_tool_call(
        tool_id: Any,
        name: Any,
        arguments: Any,
) -> Optional[Dict[str, Any]]:
    """Normalize a LlamaIndex/OpenAI tool-call representation for PyGPT."""
    if tool_id is None:
        return None
    tool_id = str(tool_id)
    if not tool_id:
        return None

    name = "" if name is None else str(name)
    if arguments in (None, ""):
        arguments = "{}"

    return {
        "id": tool_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": arguments,
        },
    }


def extract_tool_calls_from_message(message: Any) -> List[Dict[str, Any]]:
    """
    Extract native tool calls from a LlamaIndex ChatMessage.

    LlamaIndex exposes tool calls in two different shapes depending on the LLM
    wrapper/API in use:

    * ChatCompletions-style wrappers expose cumulative calls in
      ``message.additional_kwargs['tool_calls']``.
    * Responses API wrappers expose them as ``ToolCallBlock`` instances in
      ``message.blocks`` and may leave ``additional_kwargs`` empty.

    The function intentionally uses duck typing so it remains compatible with
    different LlamaIndex/OpenAI package versions without importing their
    concrete Pydantic classes here.

    :param message: LlamaIndex ChatMessage-like object
    :return: normalized PyGPT tool calls
    """
    if message is None:
        return []

    parsed: Dict[str, Dict[str, Any]] = {}

    # Newer LlamaIndex representation, including OpenAI Responses API:
    # ToolCallBlock(tool_call_id=..., tool_name=..., tool_kwargs=...).
    blocks = _get(message, "blocks", None) or []
    for block in blocks:
        tool_id = _get(block, "tool_call_id", None)
        name = _get(block, "tool_name", None)
        if tool_id is None and name is None:
            continue

        # Native Ollama /api/chat does not expose OpenAI-style tool-call IDs.
        # PyGPT's Ollama LlamaIndex adapter intentionally uses the function name
        # as the protocol identifier so a later role=tool message can map it back
        # to Ollama's required ``tool_name`` field. Keep the generic stream parser
        # compatible with that representation; otherwise the tool executes in the
        # non-stream path but streamed Chat with Files never records/preserves the
        # call for the continuation request.
        if tool_id in (None, "") and name not in (None, ""):
            tool_id = name

        call = _normalize_tool_call(
            tool_id=tool_id,
            name=name,
            arguments=_get(block, "tool_kwargs", None),
        )
        if call is not None:
            parsed[call["id"]] = call

    # ChatCompletions/OpenAI-compatible representation:
    # ChoiceDeltaToolCall / ChatCompletionMessageToolCall / dict.
    additional_kwargs = _get(message, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        tool_chunks = additional_kwargs.get("tool_calls") or []
        for tool_chunk in tool_chunks:
            function = _get(tool_chunk, "function", None)
            tool_id = _get(tool_chunk, "call_id", None) or _get(tool_chunk, "id", None)
            name = _get(tool_chunk, "name", None) or _get(function, "name", None)
            arguments = _get(tool_chunk, "arguments", None)
            if arguments is None:
                arguments = _get(function, "arguments", None)
            call = _normalize_tool_call(tool_id, name, arguments)
            if call is not None:
                parsed[call["id"]] = call

    return list(parsed.values())


def message_has_tool_calls(message: Any) -> bool:
    """Return True when a LlamaIndex ChatMessage contains native tool calls."""
    return bool(extract_tool_calls_from_message(message))


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

    calls = extract_tool_calls_from_message(getattr(chunk, "message", None))
    if calls:
        # LlamaIndex supplies cumulative tool-call state on successive streamed
        # ChatResponse objects. Keep the newest complete snapshot so parallel
        # calls are preserved as well.
        state.tool_calls.clear()
        state.tool_calls.extend(calls)

    return response
