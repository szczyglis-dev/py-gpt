#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from llama_index.core.tools import FunctionTool


CONTEXT_TOOL_NAMES = {
    "memory_ctx_get",
    "memory_ctx_add",
    "memory_ctx_replace",
}


def build_context_tools(manager, ctx):
    """Build conversation-memory tools independent of the Memory plugin.

    Advanced context handling is a core reliability feature, so Agents v2 must
    retain access to its checkpoint notes even when the optional Memory plugin is
    disabled. Normal plugin tools are deduplicated by name by the caller.
    """

    async def memory_ctx_get() -> str:
        value = manager.get_notes(ctx)
        return value or "No continuation notes are stored for this conversation."

    async def memory_ctx_add(text: str) -> str:
        return manager.add_notes(ctx, text)

    async def memory_ctx_replace(text: str) -> str:
        return manager.replace_notes(ctx, text)

    return [
        FunctionTool.from_defaults(
            async_fn=memory_ctx_get,
            name="memory_ctx_get",
            description=(
                "Read compact continuation notes for the CURRENT CONVERSATION only. "
                "These notes are not global/project memory and survive context-window trimming."
            ),
        ),
        FunctionTool.from_defaults(
            async_fn=memory_ctx_add,
            name="memory_ctx_add",
            description=(
                "Append one concise important note to continuation memory for the CURRENT CONVERSATION only. "
                "Use sparingly for goals, constraints, decisions, completed work, important findings, identifiers, "
                "or pending work that must survive context-window rollover. Each addition is stored on a new line. "
                "Parameter: text."
            ),
        ),
        FunctionTool.from_defaults(
            async_fn=memory_ctx_replace,
            name="memory_ctx_replace",
            description=(
                "Replace the complete continuation notes for the CURRENT CONVERSATION only with a concise canonical "
                "state. Use when existing notes are stale, duplicated or need consolidation. This does not modify "
                "global/project memory. Parameter: text."
            ),
        ),
    ]
