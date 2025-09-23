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
from typing import Optional, List, Dict

from PySide6.QtCore import QPointF, QSizeF
from PySide6.QtGui import (QUndoCommand)

from pygpt_net.core.node_editor.models import ConnectionModel

from .item import PortItem


# ------------------------ Undo/Redo Commands ------------------------

class AddNodeCommand(QUndoCommand):
    """Undoable command that adds a node of a given type at a scene position."""

    def __init__(self, editor: "NodeEditor", type_name: str, scene_pos: QPointF):
        """Prepare command.

        Args:
            editor: Owning NodeEditor.
            type_name: Registered node type name.
            scene_pos: Target scene position to place the node.
        """
        super().__init__(f"Add {type_name}")
        self.editor = editor
        self.type_name = type_name
        self.scene_pos = scene_pos
        self._node_uuid: Optional[str] = None

    def redo(self):
        """Create or re-add the node and its item to the scene.

        Behavior:
            - First invocation creates a fresh NodeModel from registry, applies defaults,
              and inserts it via editor._add_node_model().
            - Subsequent redos re-instantiate the NodeItem for the preserved model UUID.
        """
        if self._node_uuid is None:
            node = self.editor.graph.create_node_from_type(self.type_name)
            self.editor._prepare_new_node_defaults(node)
            self._node_uuid = node.uuid
            self.editor._add_node_model(node, self.scene_pos)
        else:
            node = self.editor._model_by_uuid(self._node_uuid)
            self.editor._add_node_item(node, self.scene_pos)

    def undo(self):
        """Remove the created node by its UUID."""
        if self._node_uuid:
            self.editor._remove_node_by_uuid(self._node_uuid)


class MoveNodeCommand(QUndoCommand):
    """Undoable command to move a node item from old_pos to new_pos."""

    def __init__(self, item: "NodeItem", old_pos: QPointF, new_pos: QPointF):
        """Store references and positions for undo/redo."""
        super().__init__("Move Node")
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):
        """Apply the new position."""
        self.item.setPos(self.new_pos)

    def undo(self):
        """Restore the old position."""
        self.item.setPos(self.old_pos)


class ResizeNodeCommand(QUndoCommand):
    """Undoable command to resize a node item from old_size to new_size."""

    def __init__(self, item: "NodeItem", old_size: QSizeF, new_size: QSizeF):
        """Store sizes for undo/redo (QSizeF copies kept)."""
        super().__init__("Resize Node")
        self.item = item
        self.old_size = QSizeF(old_size)
        self.new_size = QSizeF(new_size)

    def redo(self):
        """Apply the new size, clamped to content constraints."""
        self.item._apply_resize(self.new_size, clamp=True)

    def undo(self):
        """Restore the previous size, clamped to content constraints."""
        self.item._apply_resize(self.old_size, clamp=True)


class ConnectCommand(QUndoCommand):
    """Undoable command that creates a connection between two ports."""

    def __init__(self, editor: "NodeEditor", src: PortItem, dst: PortItem):
        """Keep enough data to restore the connection across undo/redo.

        Args:
            editor: Owning NodeEditor.
            src: Source PortItem (output).
            dst: Destination PortItem (input).
        """
        super().__init__("Connect")
        self.editor = editor
        self.src_port = src
        self.dst_port = dst
        self.src_node = src.node_item.node.uuid
        self.src_prop = src.prop_id
        self.dst_node = dst.node_item.node.uuid
        self.dst_prop = dst.prop_id
        self._conn_uuid: Optional[str] = None

    def redo(self):
        """Create the connection or re-add it by UUID."""
        if self._conn_uuid is None:
            ok, reason, conn = self.editor.graph.connect(
                (self.src_node, self.src_prop), (self.dst_node, self.dst_prop)
            )
            self.editor._dbg(f"ConnectCommand.redo (new) -> ok={ok}, reason='{reason}', new_uuid={(conn.uuid if ok else None)}")
            if ok:
                self._conn_uuid = conn.uuid
        else:
            conn = ConnectionModel(
                uuid=self._conn_uuid,
                src_node=self.src_node, src_prop=self.src_prop,
                dst_node=self.dst_node, dst_prop=self.dst_prop
            )
            ok, reason = self.editor.graph.add_connection(conn)
            self.editor._dbg(f"ConnectCommand.redo (restore) -> ok={ok}, reason='{reason}', uuid={self._conn_uuid}")

    def undo(self):
        """Remove the connection by UUID."""
        if self._conn_uuid:
            self.editor._dbg(f"ConnectCommand.undo -> remove uuid={self._conn_uuid}")
            self.editor._remove_connection_by_uuid(self._conn_uuid)


class RewireConnectionCommand(QUndoCommand):
    """Undoable command that rewires an existing connection or deletes it."""

    def __init__(self, editor: "NodeEditor",
                 old_conn: ConnectionModel,
                 new_src: Optional[PortItem],
                 new_dst: Optional[PortItem]):
        """Prepare rewire/delete action.

        Args:
            editor: Owning NodeEditor.
            old_conn: Existing connection model to replace.
            new_src: New source port (or None to delete).
            new_dst: New destination port (or None to delete).
        """
        title = "Delete Connection" if (new_src is None or new_dst is None) else "Rewire Connection"
        super().__init__(title)
        self.editor = editor
        self.old_conn_data = old_conn.to_dict()
        self.old_uuid = old_conn.uuid
        self.new_src = new_src
        self.new_dst = new_dst
        self._new_uuid: Optional[str] = None
        self._applied = False

    def redo(self):
        """Apply rewire or deletion, restoring the old connection on failure."""
        self.editor._dbg(f"RewireCommand.redo -> remove old={self.old_uuid}, new={'DELETE' if (self.new_src is None or self.new_dst is None) else 'CONNECT'}")
        self.editor._remove_connection_by_uuid(self.old_uuid)
        if self.new_src is not None and self.new_dst is not None:
            ok, reason, conn = self.editor.graph.connect(
                (self.new_src.node_item.node.uuid, self.new_src.prop_id),
                (self.new_dst.node_item.node.uuid, self.new_dst.prop_id)
            )
            self.editor._dbg(f"RewireCommand.redo connect -> ok={ok}, reason='{reason}', new_uuid={(conn.uuid if ok else None)}")
            if not ok:
                old = ConnectionModel.from_dict(self.old_conn_data)
                self.editor.graph.add_connection(old)
                self._applied = False
                return
            self._new_uuid = conn.uuid
        self._applied = True

    def undo(self):
        """Revert the rewire/delete by restoring the original connection."""
        self.editor._dbg(f"RewireCommand.undo -> restore old={self.old_uuid}, remove new={self._new_uuid}")
        if not self._applied:
            return
        if self._new_uuid:
            self._editor = self.editor
            self._editor._remove_connection_by_uuid(self._new_uuid)
        old = ConnectionModel.from_dict(self.old_conn_data)
        self.editor.graph.add_connection(old)


class ClearGraphCommand(QUndoCommand):
    """Undoable command that clears the entire graph and scene with a snapshot."""

    def __init__(self, editor: "NodeEditor"):
        """Take an internal snapshot on first redo to enable undo restoration."""
        super().__init__("Clear")
        self.editor = editor
        self._snapshot: Optional[dict] = None

    def redo(self):
        """Clear the scene and the graph, taking a snapshot if not already taken."""
        if self._snapshot is None:
            self._snapshot = self.editor.graph.to_dict()
        self.editor._dbg("ClearGraph.redo -> clearing scene+graph")
        self.editor._clear_scene_and_graph()

    def undo(self):
        """Restore the previous snapshot."""
        self._dbg = self.editor._dbg
        self._dbg("ClearGraph.undo -> restoring snapshot")
        if self._snapshot:
            self.editor.load_layout(self._snapshot)

class DeleteConnectionCommand(QUndoCommand):
    """Undoable command that deletes a single existing connection and can restore it."""

    def __init__(self, editor: "NodeEditor", conn: ConnectionModel):
        """Snapshot connection for reliable restore.

        Args:
            editor: Owning NodeEditor.
            conn: Existing ConnectionModel to delete/restore.
        """
        super().__init__("Delete Connection")
        self.editor = editor
        self.conn_uuid: Optional[str] = conn.uuid
        # Keep a serializable snapshot for undo
        self.conn_data: Dict = conn.to_dict() if hasattr(conn, "to_dict") else {
            "uuid": conn.uuid,
            "src_node": conn.src_node, "src_prop": conn.src_prop,
            "dst_node": conn.dst_node, "dst_prop": conn.dst_prop,
        }

    def redo(self):
        """Remove the connection by UUID (no-op if already gone)."""
        if self.conn_uuid and self.conn_uuid in self.editor.graph.connections:
            self.editor._remove_connection_by_uuid(self.conn_uuid)

    def undo(self):
        """Recreate the exact same connection (UUID preserved)."""
        if not self.conn_uuid:
            return
        try:
            cm = ConnectionModel.from_dict(self.conn_data)
        except Exception:
            cm = ConnectionModel(
                uuid=self.conn_data.get("uuid"),
                src_node=self.conn_data.get("src_node"),
                src_prop=self.conn_data.get("src_prop"),
                dst_node=self.conn_data.get("dst_node"),
                dst_prop=self.conn_data.get("dst_prop"),
            )
        # Best-effort restore; if add_connection fails, try connect() as fallback
        ok, _ = self.editor.graph.add_connection(cm)
        if not ok:
            self.editor.graph.connect(
                (cm.src_node, cm.src_prop),
                (cm.dst_node, cm.dst_prop),
            )
class DeleteNodeCommand(QUndoCommand):
    """Undoable command that deletes a node and all its connections, and can restore them."""

    def __init__(self, editor: "NodeEditor", item: "NodeItem"):
        """Snapshot node type, uuid, name, property values, position, size and related connections.

        Args:
            editor: Owning NodeEditor.
            item: NodeItem to delete (used only to take a snapshot at construction time).
        """
        super().__init__("Delete Node")
        self.editor = editor
        node = item.node
        self.node_uuid: str = node.uuid
        self.node_type: str = node.type
        self.node_name: str = node.name
        # Snapshot property values
        self.prop_values: Dict[str, object] = {pid: pm.value for pid, pm in node.properties.items()}
        # Snapshot UI geometry
        self.pos = QPointF(item.pos())
        self.size = QSizeF(item.size())
        # Snapshot all connections touching this node
        self._connections: List[Dict] = []
        for conn in editor.graph.connections.values():
            if conn.src_node == self.node_uuid or conn.dst_node == self.node_uuid:
                self._connections.append(conn.to_dict() if hasattr(conn, "to_dict") else {
                    "uuid": conn.uuid,
                    "src_node": conn.src_node, "src_prop": conn.src_prop,
                    "dst_node": conn.dst_node, "dst_prop": conn.dst_prop,
                })

    def redo(self):
        """Delete the node (graph will remove its connections and UI will sync via signals)."""
        self.editor._remove_node_by_uuid(self.node_uuid)

    def undo(self):
        """Recreate the node with the same UUID, restore pos/size and re-add all its connections."""
        # 1) Recreate node from registry using saved type and UUID
        try:
            node = self.editor.graph.create_node_from_type(self.node_type)
        except Exception:
            return
        try:
            node.uuid = self.node_uuid
        except Exception:
            pass
        try:
            if isinstance(self.node_name, str) and self.node_name.strip():
                node.name = self.node_name
        except Exception:
            pass

        # 2) Restore property values (casted to current spec types)
        for pid, pm in list(node.properties.items()):
            if pid in self.prop_values:
                try:
                    pm.value = self.editor._coerce_value_for_property(pm, self.prop_values[pid])
                except Exception:
                    pm.value = self.prop_values[pid]

        # 3) Place node back at original position; scene item will be created by graph signal
        self.editor._pending_node_positions[self.node_uuid] = QPointF(self.pos)
        self.editor.graph.add_node(node)

        # 4) Apply size after item exists
        item = self.editor._uuid_to_item.get(self.node_uuid)
        if item:
            try:
                item._apply_resize(QSizeF(self.size), clamp=True)
            except Exception:
                pass

        # 5) Restore connections (skip duplicates and validate ports)
        for cd in self._connections:
            cuuid = cd.get("uuid")
            # Skip if already present (could be restored by another command in a macro)
            if cuuid and cuuid in self.editor.graph.connections:
                continue
            s_n = cd.get("src_node"); s_p = cd.get("src_prop")
            d_n = cd.get("dst_node"); d_p = cd.get("dst_prop")

            # Validate node/port presence in current graph/spec
            if s_n not in self.editor.graph.nodes or d_n not in self.editor.graph.nodes:
                continue
            s_node = self.editor.graph.nodes[s_n]
            d_node = self.editor.graph.nodes[d_n]
            if s_p not in s_node.properties or d_p not in d_node.properties:
                continue

            try:
                cm = ConnectionModel(
                    uuid=cuuid if isinstance(cuuid, str) and cuuid else None,
                    src_node=s_n, src_prop=s_p,
                    dst_node=d_n, dst_prop=d_p
                )
                ok, _ = self.editor.graph.add_connection(cm)
                if not ok:
                    self.editor.graph.connect((s_n, s_p), (d_n, d_p))
            except Exception:
                # Best-effort: ignore a single failing connection to not break the undo sequence
                pass
