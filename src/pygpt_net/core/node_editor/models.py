#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.25 00:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .utils import gen_uuid


# ------------------------ Data models (pure data) ------------------------

@dataclass
class PropertyModel:
    uuid: str
    id: str
    type: str  # "slot", "str", "int", "float", "bool", "combo", "text", "HelpLabel"
    name: str
    editable: bool = True
    value: Any = None
    allowed_inputs: int = 0   # 0 none, -1 unlimited, >0 limit
    allowed_outputs: int = 0  # 0 none, -1 unlimited, >0 limit
    options: Optional[List[str]] = None  # for combo
    # UI helpers
    placeholder: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "editable": self.editable,
            "value": self.value,
            "allowed_inputs": self.allowed_inputs,
            "allowed_outputs": self.allowed_outputs,
            "options": self.options or [],
            "placeholder": self.placeholder,
            "description": self.description,
        }

    @staticmethod
    def from_dict(d: dict) -> "PropertyModel":
        return PropertyModel(
            uuid=d.get("uuid", gen_uuid()),
            id=d["id"],
            type=d["type"],
            name=d.get("name", d["id"]),
            editable=d.get("editable", True),
            value=d.get("value"),
            allowed_inputs=d.get("allowed_inputs", 0),
            allowed_outputs=d.get("allowed_outputs", 0),
            options=d.get("options") or None,
            placeholder=d.get("placeholder"),
            description=d.get("description"),
        )


@dataclass
class NodeModel:
    uuid: str
    id: str
    name: str
    type: str
    properties: Dict[str, PropertyModel] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "properties": {pid: p.to_dict() for pid, p in self.properties.items()},
        }

    @staticmethod
    def from_dict(d: dict) -> "NodeModel":
        props = {pid: PropertyModel.from_dict(pd) for pid, pd in d.get("properties", {}).items()}
        return NodeModel(
            uuid=d.get("uuid", gen_uuid()),
            id=d["id"],
            name=d.get("name", d["id"]),
            type=d["type"],
            properties=props,
        )


@dataclass
class ConnectionModel:
    uuid: str
    src_node: str
    src_prop: str
    dst_node: str
    dst_prop: str

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "src_node": self.src_node, "src_prop": self.src_prop,
            "dst_node": self.dst_node, "dst_prop": self.dst_prop,
        }

    @staticmethod
    def from_dict(d: dict) -> "ConnectionModel":
        return ConnectionModel(
            uuid=d.get("uuid", gen_uuid()),
            src_node=d["src_node"], src_prop=d["src_prop"],
            dst_node=d["dst_node"], dst_prop=d["dst_prop"],
        )