#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.25 14:00:00                  #
# ================================================== #

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class BaseNode:
    id: str
    type: str
    slots: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentNode(BaseNode):
    name: str = ""
    instruction: str = ""
    allow_remote_tools: bool = True
    allow_local_tools: bool = True
    outputs: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    memory_out: Optional[str] = None  # single mem by spec
    memory_in: List[str] = field(default_factory=list)  # not used, but kept for completeness
    role: str = ""  # Optional short description of agent's purpose


@dataclass
class StartNode(BaseNode):
    outputs: List[str] = field(default_factory=list)


@dataclass
class EndNode(BaseNode):
    inputs: List[str] = field(default_factory=list)


@dataclass
class MemoryNode(BaseNode):
    name: str = ""
    agents: List[str] = field(default_factory=list)  # agents connected to this memory


@dataclass
class FlowSchema:
    agents: Dict[str, AgentNode] = field(default_factory=dict)
    memories: Dict[str, MemoryNode] = field(default_factory=dict)
    starts: Dict[str, StartNode] = field(default_factory=dict)
    ends: Dict[str, EndNode] = field(default_factory=dict)


def _safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        if k not in cur:
            return default
        cur = cur[k]
    return cur


def parse_schema(schema: List[Dict[str, Any]]) -> FlowSchema:
    """
    Parse NodeEditor-exported schema list into FlowSchema.
    """
    fs = FlowSchema()
    for raw in schema:
        ntype = raw.get("type")
        nid = raw.get("id")
        slots = raw.get("slots", {}) or {}

        if ntype == "agent":
            node = AgentNode(
                id=nid,
                type=ntype,
                slots=slots,
                name=_safe_get(slots, "name", default=""),
                instruction=_safe_get(slots, "instruction", default=""),
                allow_remote_tools=bool(_safe_get(slots, "remote_tools", default=True)),
                allow_local_tools=bool(_safe_get(slots, "local_tools", default=True)),
                outputs=list(_safe_get(slots, "output", "out", default=[])) or [],
                inputs=list(_safe_get(slots, "input", "in", default=[])) or [],
                memory_out=(_safe_get(slots, "memory", "out", default=[None]) or [None])[0],
                memory_in=list(_safe_get(slots, "memory", "in", default=[])) or [],
                role=_safe_get(slots, "role", default="") or "",
            )
            fs.agents[nid] = node

        elif ntype == "start":
            node = StartNode(
                id=nid,
                type=ntype,
                slots=slots,
                outputs=list(_safe_get(slots, "output", "out", default=[])) or [],
            )
            fs.starts[nid] = node

        elif ntype == "end":
            node = EndNode(
                id=nid,
                type=ntype,
                slots=slots,
                inputs=list(_safe_get(slots, "input", "in", default=[])) or [],
            )
            fs.ends[nid] = node

        elif ntype == "memory":
            node = MemoryNode(
                id=nid,
                type=ntype,
                slots=slots,
                name=_safe_get(slots, "name", default=""),
                agents=list(_safe_get(slots, "input", "in", default=[])) or [],
            )
            fs.memories[nid] = node

    return fs