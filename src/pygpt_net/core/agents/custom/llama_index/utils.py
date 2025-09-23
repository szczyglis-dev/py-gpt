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
from typing import Any, Callable, Dict, List, Optional, Union

from agents import TResponseInputItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

try:
    from llama_index.core.llms import ChatMessage, MessageRole
    from llama_index.core.tools import BaseTool, FunctionTool
    from llama_index.core.llms.llm import LLM
except Exception:
    ChatMessage = None
    MessageRole = None
    BaseTool = object  # type: ignore
    FunctionTool = None
    LLM = object  # type: ignore

OptionGetter = Callable[[str, str, Any], Any]


def make_option_getter(base_agent, preset: Optional[PresetItem]) -> OptionGetter:
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
    model_name = option_get(node.id, "model", None)
    model_item: ModelItem = default_model
    try:
        if model_name:
            cand = window.core.models.get(model_name)
            if cand:
                model_item = cand
    except Exception:
        model_item = default_model

    prompt_opt = option_get(node.id, "prompt", None)
    instructions = (prompt_opt or getattr(node, "instruction", None) or base_prompt or "").strip()

    allow_local_tools = bool(
        option_get(
            node.id, "allow_local_tools",
            schema_allow_local if schema_allow_local is not None else default_allow_local
        )
    )
    allow_remote_tools = bool(
        option_get(
            node.id, "allow_remote_tools",
            schema_allow_remote if schema_allow_remote is not None else default_allow_remote
        )
    )

    return NodeRuntime(
        model=model_item,
        instructions=instructions,
        allow_local_tools=allow_local_tools,
        allow_remote_tools=allow_remote_tools,
    )


def sanitize_input_items(items: List[TResponseInputItem]) -> List[TResponseInputItem]:
    sanitized: List[TResponseInputItem] = []
    for it in items or []:
        if isinstance(it, dict):
            new_it: Dict[str, Any] = dict(it)
            new_it.pop("id", None)
            new_it.pop("message_id", None)
            if "content" in new_it and isinstance(new_it["content"], list):
                new_content = []
                for part in new_it["content"]:
                    if isinstance(part, dict):
                        p = dict(part); p.pop("id", None)
                        new_content.append(p)
                    else:
                        new_content.append(part)
                new_it["content"] = new_content
            sanitized.append(new_it)
        else:
            sanitized.append(it)
    return sanitized


def content_to_str(content: Union[str, List[Dict[str, Any]], None]) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: List[str] = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                out.append(str(part["text"]))
        return "\n".join(out)
    return ""


def to_li_chat_messages(items: List[TResponseInputItem]) -> List[ChatMessage]:
    if ChatMessage is None or MessageRole is None:
        return []
    msgs: List[ChatMessage] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        role = str(it.get("role", "")).lower()
        text = content_to_str(it.get("content"))
        if not text:
            continue
        if role == "user":
            msgs.append(ChatMessage(role=MessageRole.USER, content=text))
        elif role == "assistant":
            msgs.append(ChatMessage(role=MessageRole.ASSISTANT, content=text))
        elif role == "system":
            msgs.append(ChatMessage(role=MessageRole.SYSTEM, content=text))
        else:
            msgs.append(ChatMessage(role=MessageRole.USER, content=text))
    return msgs


def single_user_msg(text: str) -> List[ChatMessage]:
    if ChatMessage is None or MessageRole is None:
        return []
    return [ChatMessage(role=MessageRole.USER, content=text or "")]


def coerce_li_tools(function_tools: List[Any]) -> List[Any]:
    if BaseTool is object:
        return []
    tools_out: List[Any] = []
    for t in function_tools or []:
        try:
            if isinstance(t, BaseTool):
                tools_out.append(t)
            elif callable(t) and FunctionTool is not None:
                tools_out.append(FunctionTool.from_defaults(t))
            elif isinstance(t, dict):
                fn = t.get("fn") or t.get("callable")
                if callable(fn) and FunctionTool is not None:
                    tools_out.append(FunctionTool.from_defaults(fn))
        except Exception:
            continue
    return tools_out


def resolve_llm(window, node_model: ModelItem, base_llm: Any, stream: bool) -> Any:
    """
    Best practice in your app: if per-node model set -> window.core.idx.llm.get(model, stream),
    else reuse the base_llm provided from the app.
    """
    try:
        if node_model and hasattr(node_model, "name") and getattr(window.core, "idx", None):
            return window.core.idx.llm.get(node_model, stream=stream)
    except Exception:
        pass
    return base_llm


def patch_last_assistant_output(items: List[TResponseInputItem], text: str) -> List[TResponseInputItem]:
    if not items:
        return items
    patched = list(items)
    idx = None
    for i in range(len(patched) - 1, -1, -1):
        it = patched[i]
        if isinstance(it, dict) and it.get("role") == "assistant":
            idx = i
            break
    if idx is None:
        return patched
    patched[idx] = {"role": "assistant", "content": [{"type": "output_text", "text": text or ""}]}
    return sanitize_input_items(patched)

def extract_agent_text(ret: Any) -> str:
    """
    Extract plain text from various LlamaIndex agent return types.
    Prefer ret.response.message/content/text if present; avoid str(ret) which may add 'assistant:'.
    """
    try:
        resp = getattr(ret, "response", None)
        if resp is None:
            # Some agents return plain string
            return str(ret or "")
        # ChatResponse(message=LLMMessage(content=...)) or text=...
        msg = getattr(resp, "message", None)
        if msg is not None:
            # LLMMessage variants
            content = getattr(msg, "content", None) or getattr(msg, "text", None)
            if isinstance(content, str):
                return content
        text = getattr(resp, "text", None)
        if isinstance(text, str):
            return text
        # Fallback
        return str(resp)
    except Exception:
        return str(ret or "")


def strip_role_prefixes(text: str) -> str:
    """
    Remove leading 'assistant:' / 'user:' / 'system:' if leaked from stringified outputs.
    """
    if not text:
        return ""
    import re
    return re.sub(r"^\s*(assistant|user|system)\s*:\s*", "", text.strip(), flags=re.IGNORECASE)