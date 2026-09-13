#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.13 13:52:00                  #
# ================================================== #

from typing import Any, Optional


# Tool calls listed here are runtime/internal plumbing and must never be exposed
# in the conversation UI. Plugins can extend the same mechanism declaratively by
# defining a command with ``hidden=True``.
HIDDEN_TOOL_NAMES = {
    "agent_create",
    "agent_update",
    "agent_run",
    "agent_status",
    "agent_list",
    "agent_wait",
    "agent_stop",
    "agent_remove",
    "workflow_status",
    "workflow_finish",
    "delegate_task",
    "report_status",
    "shared_context",
    "swarm_start",
    "swarm_status",
}

# Hidden tools listed here remain hidden everywhere (durable storage, history,
# Tool/Tools blocks, reloads, etc.) but may be exposed by the dedicated live
# status path while they are actually executing. This list is an exception to
# presentation only; it must never be used to relax the normal hidden-tool
# persistence/rendering policy.
HIDDEN_TOOLS_REALTIME_ONLY = set()

# Code-level persistence policy for hidden tools. When False, hidden tool calls
# and their display/result cache are kept only for the live execution lifecycle
# and are not written as durable context task/tool metadata.
PERSIST_HIDDEN_TOOL_CALLS = False

# Commands declared by plugins with ``hidden=True`` are registered here while
# plugins/tool schemas are being built. Keep this separate from the static list
# above so the built-in defaults remain obvious and easy to edit.
_REGISTERED_HIDDEN_TOOL_NAMES = set()


def register_hidden_tool(name: Optional[str]) -> None:
    """Register a dynamically declared hidden tool name."""
    value = str(name or "").strip()
    if value:
        _REGISTERED_HIDDEN_TOOL_NAMES.add(value)


def register_hidden_tool_definition(definition: Any) -> None:
    """Register a command/tool definition carrying ``hidden=True``."""
    if not isinstance(definition, dict) or definition.get("hidden") is not True:
        return
    name = definition.get("cmd") or definition.get("name")
    if not name and isinstance(definition.get("function"), dict):
        name = definition["function"].get("name")
    register_hidden_tool(name)


def is_hidden_tool(name: Optional[str]) -> bool:
    """Return True when a tool is globally or dynamically hidden from the UI."""
    value = str(name or "").strip()
    return bool(
        value
        and (value in HIDDEN_TOOL_NAMES or value in _REGISTERED_HIDDEN_TOOL_NAMES)
    )


def is_hidden_tool_realtime_only(name: Optional[str]) -> bool:
    """Return True when a hidden tool may be named only in a live status row."""
    value = str(name or "").strip()
    return bool(value and value in HIDDEN_TOOLS_REALTIME_ONLY)

TOOL_EXPERT_CALL_NAME = "expert_call"
TOOL_EXPERT_CALL_DESCRIPTION = (
    "Run a named Expert as an isolated agent with its own persistent conversation memory, "
    "enabled tools and optional RAG index. Provide a complete task instruction. An optional "
    "system_prompt can temporarily specialize the agent; when supplied, the Expert preset prompt "
    "is preserved as an additional user system instruction."
)
TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION = "Expert ID from the allowed experts list"
TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION = "Required, self-contained task instruction for the expert agent"
TOOL_EXPERT_CALL_PARAM_SYSTEM_PROMPT_DESCRIPTION = (
    "Optional temporary system prompt for this expert call. If omitted, the Expert preset system "
    "prompt is used unchanged."
)
# Backward-compatible symbol for older integrations/tests. New calls use `instruction`.
TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION = TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION

TOOL_QUERY_ENGINE_NAME = "get_context"
TOOL_QUERY_ENGINE_DESCRIPTION = "Get additional context for provided question. Use this whenever you need additional context to provide an answer."
TOOL_QUERY_ENGINE_PARAM_QUERY_DESCRIPTION = "query to retrieve additional context for the question"
TOOL_QUERY_ENGINE_SPEC = ("**" + TOOL_QUERY_ENGINE_NAME + "**: "
                          + TOOL_QUERY_ENGINE_DESCRIPTION +
                     "available params: {'query': {'type': 'string', 'description': 'query string'}}, required: [query]")