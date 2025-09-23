#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from agents import TResponseInputItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem


# ---------- IO sanitization / output helpers ----------

def sanitize_input_items(items: List[TResponseInputItem]) -> List[TResponseInputItem]:
    """Remove server-assigned ids from items and content parts to avoid duplication errors."""
    sanitized: List[TResponseInputItem] = []
    for it in items or []:
        if isinstance(it, dict):
            new_it: Dict[str, Any] = dict(it)
            # top-level ids that might reappear
            new_it.pop("id", None)
            new_it.pop("message_id", None)
            # sanitize content list parts
            if "content" in new_it and isinstance(new_it["content"], list):
                new_content = []
                for part in new_it["content"]:
                    if isinstance(part, dict):
                        p = dict(part)
                        p.pop("id", None)
                        new_content.append(p)
                    else:
                        new_content.append(part)
                new_it["content"] = new_content
            sanitized.append(new_it)
        else:
            sanitized.append(it)
    return sanitized


def extract_text_output(result: Any) -> str:
    """
    Best-effort to get a human-facing text from openai-agents Runner result
    without relying on app-specific helpers.
    """
    out = getattr(result, "final_output", None)
    if out is None:
        return ""
    try:
        return str(out)
    except Exception:
        return ""


def patch_last_assistant_output(items: List[TResponseInputItem], text: str) -> List[TResponseInputItem]:
    """
    Replace the content of the last assistant message with plain text content.
    This prevents leaking router JSON to subsequent agents.
    """
    if not items:
        return items
    patched = list(items)
    # find last assistant
    idx: Optional[int] = None
    for i in range(len(patched) - 1, -1, -1):
        it = patched[i]
        if isinstance(it, dict) and it.get("role") == "assistant":
            idx = i
            break
    if idx is None:
        return patched

    # set standard output_text content
    patched[idx] = {
        "role": "assistant",
        "content": [
            {
                "type": "output_text",
                "text": text or "",
            }
        ],
    }
    return sanitize_input_items(patched)


# ---------- Per-agent options resolution ----------

OptionGetter = Callable[[str, str, Any], Any]


def make_option_getter(base_agent, preset: Optional[PresetItem]) -> OptionGetter:
    """
    Returns option_get(section, key, default) bound to your BaseAgent.get_option semantics.
    section == node.id (e.g. "agent_1"), key in {"model","prompt","allow_local_tools","allow_remote_tools"}.
    """
    def option_get(section: str, key: str, default: Any = None) -> Any:
        if preset is None:
            return default
        try:
            val = base_agent.get_option(preset, section, key)
            return default if val in (None, "") else val
        except Exception:
            return default
    return option_get


@dataclass
class NodeRuntime:
    model: ModelItem
    instructions: str
    allow_local_tools: bool
    allow_remote_tools: bool


def resolve_node_runtime(
    *,
    window,
    node,
    option_get: OptionGetter,
    default_model: ModelItem,
    base_prompt: Optional[str],
    schema_allow_local: Optional[bool],
    schema_allow_remote: Optional[bool],
    default_allow_local: bool,
    default_allow_remote: bool,
) -> NodeRuntime:
    """
    Resolve per-node runtime using get_option() overrides, schema slots and defaults.

    Priority:
    - model:      get_option(node.id, "model") -> window.core.models.get(name) -> default_model
    - prompt:     get_option(node.id, "prompt") -> node.instruction -> base_prompt -> ""
    - allow_*:    get_option(node.id, "allow_local_tools"/"allow_remote_tools")
                  -> schema flags -> defaults
    """
    # Model resolve
    model_name = option_get(node.id, "model", None)
    model_item: ModelItem = default_model
    try:
        if model_name:
            cand = window.core.models.get(model_name)
            if cand:
                model_item = cand
    except Exception:
        # fallback to default_model
        model_item = default_model

    # Instructions resolve
    prompt_opt = option_get(node.id, "prompt", None)
    instructions = (prompt_opt or getattr(node, "instruction", None) or base_prompt or "").strip()

    # Tools flags resolve
    allow_local_tools = bool(
        option_get(
            node.id,
            "allow_local_tools",
            schema_allow_local if schema_allow_local is not None else default_allow_local,
        )
    )
    allow_remote_tools = bool(
        option_get(
            node.id,
            "allow_remote_tools",
            schema_allow_remote if schema_allow_remote is not None else default_allow_remote,
        )
    )

    return NodeRuntime(
        model=model_item,
        instructions=instructions,
        allow_local_tools=allow_local_tools,
        allow_remote_tools=allow_remote_tools,
    )