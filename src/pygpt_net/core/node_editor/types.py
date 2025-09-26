#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 12:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# ------------------------ Types registry (templates) ------------------------

@dataclass
class PropertySpec:
    id: str
    type: str
    name: Optional[str] = None
    editable: bool = True
    value: Any = None
    allowed_inputs: int = 0
    allowed_outputs: int = 0
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None      # hint text for text editors
    description: Optional[str] = None      # tooltip/help text shown in UI


@dataclass
class NodeTypeSpec:
    type_name: str
    title: Optional[str] = None
    properties: List[PropertySpec] = field(default_factory=list)
    # Below are optional extensions for agent-flow needs:
    base_id: Optional[str] = None        # base prefix for friendly ids, e.g. "agent"
    export_kind: Optional[str] = None    # short kind for export, e.g. "agent", "start"
    bg_color: Optional[str] = None       # optional per-type background color (CSS/hex)
    max_num: Optional[int] = None        # optional per-layout cap; None or <=0 means unlimited

class NodeTypeRegistry:
    """Registry for node type specifications. Extend/override in subclasses."""
    def __init__(self, empty: bool = False):
        self._types: Dict[str, NodeTypeSpec] = {}
        if not empty:
            self._install_default_types()

    def register(self, spec: NodeTypeSpec):
        self._types[spec.type_name] = spec

    def types(self) -> List[str]:
        return list(self._types.keys())

    def get(self, type_name: str) -> Optional[NodeTypeSpec]:
        return self._types.get(type_name)

    def _install_default_types(self):
        # Example/basic nodes kept intact
        self.register(NodeTypeSpec(
            type_name="Value/Float",
            title="Float",
            properties=[
                PropertySpec(id="value", type="float", name="Value", editable=True, value=0.0,
                             allowed_inputs=0, allowed_outputs=1),
            ]
        ))
        self.register(NodeTypeSpec(
            type_name="Math/Add",
            title="Add",
            properties=[
                PropertySpec(id="A", type="float", name="A", editable=True, value=0.0, allowed_inputs=1, allowed_outputs=0),
                PropertySpec(id="B", type="float", name="B", editable=True, value=0.0, allowed_inputs=1, allowed_outputs=0),
                PropertySpec(id="result", type="float", name="Result", editable=False, value=None, allowed_inputs=0, allowed_outputs=1),
            ]
        ))
        # Tip: to allow multiple connections to an input or output, set allowed_inputs/allowed_outputs to -1.