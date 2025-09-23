#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 00:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import re

from PySide6.QtCore import QObject, Signal

from .models import NodeModel, ConnectionModel, PropertyModel
from .types import NodeTypeRegistry
from .utils import gen_uuid


# ------------------------ Graph (Qt QObject + signals) ------------------------

class NodeGraph(QObject):
    """In-memory node graph with Qt signals, easily serializable."""
    nodeAdded = Signal(object)            # NodeModel
    nodeRemoved = Signal(str)             # node uuid
    connectionAdded = Signal(object)      # ConnectionModel
    connectionRemoved = Signal(str)       # connection uuid
    cleared = Signal()
    propertyValueChanged = Signal(str, str, object)  # node_uuid, prop_id, new_value

    def __init__(self, registry: Optional[NodeTypeRegistry] = None):
        super().__init__()
        self.registry = registry or NodeTypeRegistry()
        self.nodes: Dict[str, NodeModel] = {}
        self.connections: Dict[str, ConnectionModel] = {}
        self._node_counter = 1
        # Per-base_id counters for friendly IDs (persisted with layout)
        self._id_counters: Dict[str, int] = {}

    # -------- ID helpers (friendly unique IDs per base prefix) --------

    @staticmethod
    def _slug_from_type_name(type_name: str) -> str:
        # fallback base id from type name: last segment lowercased, non-words to underscore
        base = type_name.split("/")[-1].lower()
        base = re.sub(r"\W+", "_", base).strip("_")
        return base or "node"

    def _next_id_for_base(self, base: str) -> str:
        n = self._id_counters.get(base, 0) + 1
        self._id_counters[base] = n
        return f"{base}_{n}"

    def _seed_counters_from_existing(self):
        # Scan existing node ids like 'agent_12' and seed counters to max per base
        for node in self.nodes.values():
            m = re.match(r"^([a-zA-Z0-9]+)_(\d+)$", node.id)
            if not m:
                continue
            base, num = m.group(1), int(m.group(2))
            cur = self._id_counters.get(base, 0)
            if num > cur:
                self._id_counters[base] = num

    # -------- Creation / mutation --------

    def create_node_from_type(self, type_name: str, name: Optional[str] = None) -> NodeModel:
        spec = self.registry.get(type_name)
        if not spec:
            raise ValueError(f"Unknown node type: {type_name}")

        base_id = spec.base_id or self._slug_from_type_name(type_name)
        # Generate friendly id if base configured; otherwise fallback to generic Node-#
        if spec.base_id:
            nid = self._next_id_for_base(base_id)
        else:
            nid = f"Node-{self._node_counter}"
            self._node_counter += 1

        props: Dict[str, PropertyModel] = {}
        for ps in spec.properties:
            props[ps.id] = PropertyModel(
                uuid=gen_uuid(), id=ps.id, type=ps.type, name=ps.name or ps.id,
                editable=ps.editable, value=ps.value,
                allowed_inputs=ps.allowed_inputs, allowed_outputs=ps.allowed_outputs,
                options=ps.options
            )
        # Auto inject read-only 'base_id' property for visibility if base_id defined and not present
        if spec.base_id and "base_id" not in props:
            props["base_id"] = PropertyModel(
                uuid=gen_uuid(), id="base_id", type="str", name="Base ID",
                editable=False, value=base_id, allowed_inputs=0, allowed_outputs=0
            )

        node = NodeModel(uuid=gen_uuid(), id=nid, name=name or spec.title or nid, type=type_name, properties=props)
        return node

    def add_node(self, node: NodeModel):
        self.nodes[node.uuid] = node
        # Ensure counters are aware of externally provided nodes
        m = re.match(r"^([a-zA-Z0-9]+)_(\d+)$", node.id)
        if m:
            base, num = m.group(1), int(m.group(2))
            if self._id_counters.get(base, 0) < num:
                self._id_counters[base] = num
        self.nodeAdded.emit(node)

    def remove_node(self, node_uuid: str):
        to_remove = [cid for cid, c in self.connections.items()
                     if c.src_node == node_uuid or c.dst_node == node_uuid]
        for cid in to_remove:
            self.remove_connection(cid)
        if node_uuid in self.nodes:
            del self.nodes[node_uuid]
            self.nodeRemoved.emit(node_uuid)

    def can_connect(self, src: Tuple[str, str], dst: Tuple[str, str]) -> Tuple[bool, str]:
        src_node_uuid, src_prop_id = src
        dst_node_uuid, dst_prop_id = dst
        if src_node_uuid == dst_node_uuid and src_prop_id == dst_prop_id:
            return False, "Cannot connect a port to itself."
        src_node = self.nodes.get(src_node_uuid)
        dst_node = self.nodes.get(dst_node_uuid)
        if not src_node or not dst_node:
            return False, "Node not found."
        sp = src_node.properties.get(src_prop_id)
        dp = dst_node.properties.get(dst_prop_id)
        if not sp or not dp:
            return False, "Property not found."
        if sp.allowed_outputs == 0:
            return False, "Source has no outputs."
        if dp.allowed_inputs == 0:
            return False, "Destination has no inputs."
        if sp.type != dp.type:
            return False, f"Type mismatch: {sp.type} -> {dp.type}"
        if dp.allowed_inputs > 0:
            count = sum(1 for c in self.connections.values()
                        if c.dst_node == dst_node_uuid and c.dst_prop == dst_prop_id)
            if count >= dp.allowed_inputs:
                return False, "Destination input limit reached."
        if sp.allowed_outputs > 0:
            count = sum(1 for c in self.connections.values()
                        if c.src_node == src_node_uuid and c.src_prop == src_prop_id)
            if count >= sp.allowed_outputs:
                return False, "Source output limit reached."
        return True, ""

    def add_connection(self, conn: ConnectionModel) -> Tuple[bool, str]:
        ok, reason = self.can_connect((conn.src_node, conn.src_prop), (conn.dst_node, conn.dst_prop))
        if not ok:
            return False, reason
        for c in self.connections.values():
            if c.src_node == conn.src_node and c.src_prop == conn.src_prop and \
               c.dst_node == conn.dst_node and c.dst_prop == conn.dst_prop:
                return False, "Connection already exists."
        self.connections[conn.uuid] = conn
        self.connectionAdded.emit(conn)
        return True, ""

    def connect(self, src: Tuple[str, str], dst: Tuple[str, str]) -> Tuple[bool, str, Optional[ConnectionModel]]:
        conn = ConnectionModel(uuid=gen_uuid(), src_node=src[0], src_prop=src[1], dst_node=dst[0], dst_prop=dst[1])
        ok, reason = self.add_connection(conn)
        return ok, reason, conn if ok else None

    def remove_connection(self, conn_uuid: str):
        if conn_uuid in self.connections:
            del self.connections[conn_uuid]
            self.connectionRemoved.emit(conn_uuid)

    def set_property_value(self, node_uuid: str, prop_id: str, value: Any):
        node = self.nodes.get(node_uuid)
        if not node:
            return
        prop = node.properties.get(prop_id)
        if not prop or not prop.editable:
            return
        prop.value = value
        self.propertyValueChanged.emit(node_uuid, prop_id, value)

    def to_dict(self) -> dict:
        return {
            "nodes": {nuuid: n.to_dict() for nuuid, n in self.nodes.items()},
            "connections": {c.uuid: c.to_dict() for c in self.connections.values()},
            "_node_counter": self._node_counter,
            "_id_counters": dict(self._id_counters),
        }

    def to_schema(self) -> dict:
        nodes_out: Dict[str, dict] = {}
        for nuuid, n in self.nodes.items():
            nodes_out[nuuid] = {
                "type": n.type,
                "id": n.id,
                "name": n.name,
                "values": {pid: p.value for pid, p in n.properties.items()},
            }
        conns_out = [{"src": [c.src_node, c.src_prop], "dst": [c.dst_node, c.dst_prop]}
                     for c in self.connections.values()]
        return {"nodes": nodes_out, "connections": conns_out}

    # --- Export to list schema (list of nodes with slots/in-out) ---
    def to_list_schema(self) -> List[dict]:
        # Build helper maps
        uuid_to_node: Dict[str, NodeModel] = dict(self.nodes)
        uuid_to_id: Dict[str, str] = {u: n.id for u, n in uuid_to_node.items()}
        # Pre-index connections by (node_uuid, prop_id)
        incoming: Dict[Tuple[str, str], List[str]] = {}
        outgoing: Dict[Tuple[str, str], List[str]] = {}
        for c in self.connections.values():
            outgoing.setdefault((c.src_node, c.src_prop), []).append(uuid_to_id.get(c.dst_node, c.dst_node))
            incoming.setdefault((c.dst_node, c.dst_prop), []).append(uuid_to_id.get(c.src_node, c.src_node))

        result: List[dict] = []
        for n in uuid_to_node.values():
            spec = self.registry.get(n.type)
            kind = spec.export_kind if spec and spec.export_kind else n.type.split("/")[-1].lower()
            slots: Dict[str, Any] = {}
            for pid, prop in n.properties.items():
                is_port = (prop.allowed_inputs != 0) or (prop.allowed_outputs != 0)
                if is_port:
                    slots[pid] = {
                        "in": list(incoming.get((n.uuid, pid), [])),
                        "out": list(outgoing.get((n.uuid, pid), [])),
                    }
                else:
                    # Skip internal helper fields if needed
                    if pid == "base_id":
                        continue
                    slots[pid] = prop.value
            result.append({
                "type": kind,
                "id": n.id,
                "slots": slots,
            })

        # Stable order by id
        result.sort(key=lambda d: d["id"])
        return result

    def from_dict(self, d: dict):
        self.clear(silent=True)
        nodes_d = d.get("nodes", {})
        for nuuid, nd in nodes_d.items():
            node = NodeModel.from_dict(nd)
            self.nodes[node.uuid] = node
        conns_d = d.get("connections", {})
        for cid, cd in conns_d.items():
            conn = ConnectionModel.from_dict(cd)
            self.connections[conn.uuid] = conn
        self._node_counter = d.get("_node_counter", len(self.nodes) + 1)
        self._id_counters = dict(d.get("_id_counters", {}))
        # Seed counters from existing node ids if counters were not present
        if not self._id_counters:
            self._seed_counters_from_existing()
        for n in self.nodes.values():
            self.nodeAdded.emit(n)
        for c in self.connections.values():
            self.connectionAdded.emit(c)

    def clear(self, silent: bool = False):
        self.nodes.clear()
        self.connections.clear()
        # Reset counters to keep friendly IDs strictly per-layout.
        # After a clear, numbering starts again from 1 for each base prefix.
        self._node_counter = 1
        self._id_counters.clear()
        if not silent:
            self.cleared.emit()