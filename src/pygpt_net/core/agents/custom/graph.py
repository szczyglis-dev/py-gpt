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
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .schema import FlowSchema, AgentNode, StartNode, EndNode, MemoryNode


@dataclass
class FlowGraph:
    schema: FlowSchema
    adjacency: Dict[str, List[str]] = field(default_factory=dict)  # node_id -> list of node_ids
    agent_to_memory: Dict[str, Optional[str]] = field(default_factory=dict)  # agent_id -> mem_id or None
    start_targets: List[str] = field(default_factory=list)  # immediate next nodes from start
    end_nodes: List[str] = field(default_factory=list)  # ids of end nodes

    def get_next(self, node_id: str) -> List[str]:
        return self.adjacency.get(node_id, [])

    def first_connected_end(self, node_id: str) -> Optional[str]:
        outs = self.get_next(node_id)
        for out in outs:
            if out in self.schema.ends:
                return out
        return None

    def pick_default_start_agent(self) -> Optional[str]:
        """Pick lowest numeric agent id if no start is present."""
        if not self.schema.agents:
            return None
        # Prefer numeric suffix; fallback to lexicographic
        def key_fn(aid: str) -> Tuple[int, str]:
            m = re.search(r"(\d+)$", aid)
            if m:
                try:
                    return (int(m.group(1)), aid)
                except Exception:
                    pass
            return (10**9, aid)

        return sorted(self.schema.agents.keys(), key=key_fn)[0]


def build_graph(fs: FlowSchema) -> FlowGraph:
    g = FlowGraph(schema=fs)
    # adjacency from agents
    for aid, anode in fs.agents.items():
        g.adjacency[aid] = list(anode.outputs or [])
        g.agent_to_memory[aid] = anode.memory_out

    # adjacency from start nodes
    g.end_nodes = list(fs.ends.keys())
    g.start_targets = []
    if fs.starts:
        # By spec there can be multiple start nodes; we concatenate their outputs in order found
        for sid, snode in fs.starts.items():
            g.adjacency[sid] = list(snode.outputs or [])
            g.start_targets.extend(snode.outputs or [])

    return g