#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.25 12:05:00                  #
# ================================================== #

from __future__ import annotations
from typing import Dict, Optional, List, Tuple, Any, Union, Callable

from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QSizeF, Property, QEvent
from PySide6.QtGui import QAction, QColor, QUndoStack, QPalette, QCursor, QKeySequence, QShortcut, QFont
from PySide6.QtWidgets import (
    QWidget, QApplication, QGraphicsView, QMenu, QMessageBox, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QPlainTextEdit, QLabel
)

from pygpt_net.core.node_editor.graph import NodeGraph
from pygpt_net.core.node_editor.types import NodeTypeRegistry
from pygpt_net.core.node_editor.models import NodeModel, PropertyModel, ConnectionModel

from pygpt_net.utils import trans

from .command import AddNodeCommand, ClearGraphCommand, RewireConnectionCommand, ConnectCommand, DeleteNodeCommand, DeleteConnectionCommand
from .item import EdgeItem, PortItem
from .node import NodeItem
from .view import NodeGraphicsScene, NodeGraphicsView, NodeViewOverlayControls, NodeViewStatusLabel
from .utils import _qt_is_valid
from .config import EditorConfig


# ------------------------ NodeEditor ------------------------

class NodeEditor(QWidget):
    """Main widget embedding a QGraphicsView-based node editor.

    Responsibilities:
        - Owns NodeGraph and keeps it in sync with scene items (NodeItem/EdgeItem).
        - Manages user interactions: add/move/resize nodes, connect/rewire/delete edges.
        - Provides save/load layout (schema-agnostic) and undo/redo integration.
        - Applies theming and propagates style/palette to embedded editors.
    """

    def _q_set(self, name, value):
        """Qt property writer: set attribute and refresh theme if ready."""
        setattr(self, name, value)
        if not getattr(self, "_ready_for_theme", True):
            return
        if not getattr(self, "_alive", True):
            return
        if getattr(self, "view", None) is None:
            return
        try:
            self._update_theme()
        except Exception:
            pass

    def _q_set_bool(self, name, value: bool):
        """Qt property writer for booleans."""
        setattr(self, name, bool(value))

    # Default theme colors and interaction parameters (Qt Properties are declared below)
    _node_bg_color = QColor(45, 45, 48)
    _node_border_color = QColor(80, 80, 90)
    _node_selection_color = QColor(255, 170, 0)
    _node_title_color = QColor(60, 60, 63)
    _port_input_color = QColor(100, 180, 255)
    _port_output_color = QColor(140, 255, 140)
    _port_connected_color = QColor(255, 220, 100)
    _port_accept_color = QColor(255, 255, 140)
    _edge_color = QColor(180, 180, 180)
    _edge_selected_color = QColor(255, 140, 90)
    _grid_back_color = QColor(35, 35, 38)
    _grid_pen_color = QColor(55, 55, 60)

    _port_label_color = QColor(220, 220, 220)
    _port_capacity_color = QColor(200, 200, 200)

    _edge_pick_width: float = 12.0
    _resize_grip_margin: float = 12.0
    _resize_grip_hit_inset: float = 5.0
    _port_pick_radius: float = 10.0
    _port_click_rewire_if_connected: bool = True
    _rewire_drop_deletes: bool = True

    # Expose appearance/interaction knobs as Qt Properties (useful for Designer/QML bindings)
    nodeBackgroundColor = Property(QColor, lambda self: self._node_bg_color, lambda self, v: self._q_set("_node_bg_color", v))
    nodeBorderColor = Property(QColor, lambda self: self._node_border_color, lambda self, v: self._q_set("_node_border_color", v))
    nodeSelectionColor = Property(QColor, lambda self: self._node_selection_color, lambda self, v: self._q_set("_node_selection_color", v))
    nodeTitleColor = Property(QColor, lambda self: self._node_title_color, lambda self, v: self._q_set("_node_title_color", v))
    portInputColor = Property(QColor, lambda self: self._port_input_color, lambda self, v: self._q_set("_port_input_color", v))
    portOutputColor = Property(QColor, lambda self: self._port_output_color, lambda self, v: self._q_set("_port_output_color", v))
    portConnectedColor = Property(QColor, lambda self: self._port_connected_color, lambda self, v: self._q_set("_port_connected_color", v))
    portAcceptColor = Property(QColor, lambda self: self._port_accept_color, lambda self, v: self._q_set("_port_accept_color", v))
    edgeColor = Property(QColor, lambda self: self._edge_color, lambda self, v: self._q_set("_edge_color", v))
    edgeSelectedColor = Property(QColor, lambda self: self._edge_selected_color, lambda self, v: self._q_set("_edge_selected_color", v))
    gridBackColor = Property(QColor, lambda self: self._grid_back_color, lambda self, v: self._q_set("_grid_back_color", v))
    gridPenColor = Property(QColor, lambda self: self._grid_pen_color, lambda self, v: self._q_set("_grid_pen_color", v))

    portLabelColor = Property(QColor, lambda self: self._port_label_color, lambda self, v: self._q_set("_port_label_color", v))
    portCapacityColor = Property(QColor, lambda self: self._port_capacity_color, lambda self, v: self._q_set("_port_capacity_color", v))

    edgePickWidth = Property(float, lambda self: self._edge_pick_width, lambda self, v: self._set_edge_pick_width(v))
    resizeGripMargin = Property(float, lambda self: self._resize_grip_margin, lambda self, v: self._q_set("_resize_grip_margin", float(v)))
    resizeGripHitInset = Property(float, lambda self: self._resize_grip_hit_inset, lambda self, v: self._set_resize_grip_hit_inset(float(v)))
    portPickRadius = Property(float, lambda self: self._port_pick_radius, lambda self, v: self._q_set("_port_pick_radius", float(v)))
    portClickRewireIfConnected = Property(bool, lambda self: self._port_click_rewire_if_connected, lambda self, v: self._q_set_bool("_port_click_rewire_if_connected", v))
    rewireDropDeletes = Property(bool, lambda self: self._rewire_drop_deletes, lambda self, v: self._q_set_bool("_rewire_drop_deletes", v))

    def _set_resize_grip_hit_inset(self, v: float):
        """Setter that also re-applies size on all items to refresh hit regions."""
        self._resize_grip_hit_inset = max(0.0, float(v))
        for item in list(self._uuid_to_item.values()):
            if _qt_is_valid(item):
                item._apply_resize(item.size(), clamp=True)
        if _qt_is_valid(self.view):
            self.view.viewport().update()

    def _set_edge_pick_width(self, v: float):
        """Setter that recomputes shapes for all edges (including interactive)."""
        self._edge_pick_width = float(v) if v and v > 0 else 12.0
        for edge in list(self._conn_uuid_to_edge.values()):
            if _qt_is_valid(edge):
                edge.prepareGeometryChange()
                edge.update()
        if getattr(self, "_interactive_edge", None) and _qt_is_valid(self._interactive_edge):
            self._interactive_edge.prepareGeometryChange()
            self._interactive_edge.update()
        if _qt_is_valid(self.view):
            self.view.viewport().update()

    def __init__(self, parent: Optional[WIDGET] = None, registry: Optional[NodeTypeRegistry] = None, config: Optional[EditorConfig] = None):
        """Initialize the editor, scene, view, graph and interaction state."""
        super().__init__(parent)
        self.setObjectName("NodeEditor")
        self._debug = False
        self._dbg("INIT NodeEditor")

        # Centralized strings
        self.config: EditorConfig = config if isinstance(config, EditorConfig) else EditorConfig()

        self.graph = NodeGraph(registry)
        self.scene = NodeGraphicsScene(self)
        self.view = NodeGraphicsView(self.scene, self)
        self.view.setGeometry(self.rect())
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._undo = QUndoStack(self)
        self._uuid_to_item: Dict[str, NodeItem] = {}
        self._conn_uuid_to_edge: Dict[str, EdgeItem] = {}
        self._interactive_edge: Optional[EdgeItem] = None
        self._interactive_src_port: Optional[PortItem] = None
        self._hover_candidate: Optional[PortItem] = None
        self._pending_node_positions: Dict[str, QPointF] = {}

        self._wire_state: str = "idle"
        self._rewire_conn_uuid: Optional[str] = None
        self._rewire_hidden_edge: Optional[EdgeItem] = None
        self._rewire_fixed_src: Optional[PortItem] = None
        self._rewire_press_scene_pos: Optional[QPointF] = None

        self._spawn_origin: Optional[QPointF] = None
        self._spawn_index: int = 0
        self._saved_drag_mode: Optional[QGraphicsView.DragMode] = None

        # Collisions on/off flag
        self.enable_collisions: bool = False
        # Top Z counter for new nodes when collisions are disabled (keeps newest on top)
        self._z_top: float = 2.0

        # External guard for scene editing/menu (callable bool); when None -> allowed
        self.editing_allowed: Optional[Callable[[], bool]] = None

        self.scene.sceneContextRequested.connect(self._on_scene_context_menu)
        self.graph.nodeAdded.connect(self._on_graph_node_added)
        self.graph.nodeRemoved.connect(self._on_graph_node_removed)
        self.graph.connectionAdded.connect(self._on_graph_connection_added)
        self.graph.connectionRemoved.connect(self._on_graph_connection_removed)
        self.graph.cleared.connect(self._on_graph_cleared)

        self.scene.installEventFilter(self)

        self._alive = True
        self._closing = False
        self._ready_for_theme = True
        self.destroyed.connect(self._on_destroyed)
        self.on_clear = None

        # Tracks if a layout is being loaded; prevents auto-renumbering during import.
        self._is_loading_layout: bool = False

        # Track whether a text-like editor currently has focus (robust against QGraphicsProxyWidget)
        self._text_input_active: bool = False
        app = QApplication.instance()
        if app:
            app.focusChanged.connect(self._on_focus_changed)

        # Delete shortcut handled at editor-level; never handled by the view
        self._shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self._shortcut_delete.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_delete.activated.connect(self._on_delete_shortcut)

        # Per-layout Base ID counters: {property_id -> {base_string -> max_suffix_used}}
        # These counters are rebuilt on load_layout() and reset on clear.
        self._base_id_max: Dict[str, Dict[str, int]] = {}
        self._reset_base_id_counters()

        # Top-right overlay controls (Grab, Zoom Out, Zoom In)
        self._controls = NodeViewOverlayControls(self)
        self._controls.grabToggled.connect(self._on_grab_toggled)
        self._controls.zoomInClicked.connect(self.zoom_in)
        self._controls.zoomOutClicked.connect(self.zoom_out)
        self._controls.raise_()

        # Bottom-left fixed status label
        self._status = NodeViewStatusLabel(self)
        self._status.raise_()

    # ---------- Debug helper ----------
    def _dbg(self, msg: str):
        """Conditional debug logger (enabled by self._debug)."""
        if self._debug:
            print(f"[NodeEditor][{hex(id(self))}] {msg}")

    # Focus tracking to detect if the user is typing in an input
    def _is_text_entry_widget(self, w: Optional[QWidget]) -> bool:
        """Return True if the widget is a focused, editable text-like editor."""
        if w is None:
            return False
        try:
            if isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit)):
                if hasattr(w, "isReadOnly") and w.isReadOnly():
                    return False
                return True
            if isinstance(w, QComboBox):
                return w.isEditable() and w.hasFocus()
            if isinstance(w, (QSpinBox, QDoubleSpinBox)):
                return w.hasFocus()
        except Exception:
            return False
        return False

    def _on_focus_changed(self, old: Optional[QWidget], now: Optional[QWidget]):
        """Update internal flag when focus moves to/from text widgets."""
        self._text_input_active = self._is_text_entry_widget(now)

    # ---------- QWidget overrides ----------

    def _on_destroyed(self):
        """Set flags and disconnect global signals on destruction."""
        self._alive = False
        self._ready_for_theme = False
        try:
            app = QApplication.instance()
            if app:
                app.focusChanged.disconnect(self._on_focus_changed)
        except Exception:
            pass

    def closeEvent(self, e):
        """Perform a thorough cleanup to prevent dangling Qt wrappers during shutdown."""
        self._dbg("closeEvent -> full cleanup")

        # Make the editor effectively inert for any in-flight events
        self._closing = True
        self._alive = False
        self._ready_for_theme = False

        # Stop listening to global focus changes
        try:
            app = QApplication.instance()
            if app:
                app.focusChanged.disconnect(self._on_focus_changed)
        except Exception:
            pass

        # Disconnect scene signals and filters
        try:
            if _qt_is_valid(self.scene):
                self.scene.sceneContextRequested.disconnect(self._on_scene_context_menu)
        except Exception:
            pass

        # Cancel any interactive wire state before clearing items
        self._reset_interaction_states(remove_hidden_edges=True)

        try:
            if _qt_is_valid(self.scene):
                self.scene.removeEventFilter(self)
        except Exception:
            pass

        # Disconnect graph signals early to prevent callbacks during teardown
        self._disconnect_graph_signals()

        # Clear undo stack to drop references to scene items and widgets
        try:
            if self._undo is not None:
                self._undo.clear()
        except Exception:
            pass

        # Proxies/widgets first (prevents QWidget-in-scene dangling)
        self._cleanup_node_proxies()

        # Remove edge items, then all remaining scene items
        try:
            self._remove_all_edge_items_from_scene()
            if _qt_is_valid(self.scene):
                self.scene.clear()
        except Exception:
            pass

        # Detach view from scene to break mutual references
        try:
            if _qt_is_valid(self.view):
                self.view.setScene(None)
        except Exception:
            pass

        # Drop internal maps to help GC
        try:
            self._uuid_to_item.clear()
            self._conn_uuid_to_edge.clear()
        except Exception:
            pass
        self._interactive_edge = None
        self._interactive_src_port = None
        self._hover_candidate = None
        self._pending_node_positions.clear()

        # Optionally schedule deletion of scene/view
        try:
            if _qt_is_valid(self.scene):
                self.scene.deleteLater()
        except Exception:
            pass
        try:
            if _qt_is_valid(self.view):
                self.view.deleteLater()
        except Exception:
            pass

        self.scene = None
        self.view = None

        # Force-flush all deferred deletions to avoid old wrappers lingering into the next open
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QEvent
            for _ in range(3):
                QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
                QApplication.processEvents()
        except Exception:
            pass

        super().closeEvent(e)

    def _disconnect_graph_signals(self):
        """Disconnect all graph signals safely (ignore if already disconnected)."""
        for signal, slot in (
            (self.graph.nodeAdded, self._on_graph_node_added),
            (self.graph.nodeRemoved, self._on_graph_node_removed),
            (self.graph.connectionAdded, self._on_graph_connection_added),
            (self.graph.connectionRemoved, self._on_graph_connection_removed),
            (self.graph.cleared, self._on_graph_cleared),
        ):
            try:
                signal.disconnect(slot)
            except Exception:
                pass

    def resizeEvent(self, e):
        """Keep the view sized to the editor widget and position overlays."""
        if _qt_is_valid(self.view):
            self.view.setGeometry(self.rect())
        # Position overlays
        self._position_overlay_controls()
        self._position_status_label()
        super().resizeEvent(e)

    def showEvent(self, e):
        """Cache the spawn origin, reapply stylesheets and position overlays."""
        if self._spawn_origin is None and _qt_is_valid(self.view):
            self._spawn_origin = self.view.mapToScene(self.view.viewport().rect().center())
        self._reapply_stylesheets()
        # Ensure overlays are placed after the widget becomes visible
        self._position_overlay_controls()
        self._position_status_label()
        self._update_status_label()
        super().showEvent(e)

    def event(self, e):
        """React to global style/palette changes and reset interactions on focus loss."""
        et = e.type()
        # Do not accept ShortcutOverride here; we rely on the editor-level QShortcut for Delete.
        if et in (QEvent.StyleChange, QEvent.PaletteChange, QEvent.FontChange,
                  QEvent.ApplicationPaletteChange, QEvent.ApplicationFontChange):
            self._reapply_stylesheets()
        if et in (QEvent.FocusOut, QEvent.WindowDeactivate):
            self._dbg("event -> focus out/window deactivate -> reset interaction")
            self._reset_interaction_states(remove_hidden_edges=False)
        return super().event(e)

    def _position_overlay_controls(self):
        """Place the top-right overlay controls with 10px margin."""
        try:
            if _qt_is_valid(self._controls):
                sz = self._controls.sizeHint()
                x = max(10, self.width() - sz.width() - 10)
                y = 10
                self._controls.move(x, y)
                self._controls.raise_()
                self._controls.show()
        except Exception:
            pass

    def _position_status_label(self):
        """Place bottom-left status label with 10px margin."""
        try:
            if _qt_is_valid(self._status):
                s = self._status.sizeHint()
                x = 10
                y = max(10, self.height() - s.height() - 10)
                self._status.move(x, y)
                self._status.raise_()
                self._status.show()
        except Exception:
            pass

    # ---------- Public API ----------

    def add_node(self, type_name: str, scene_pos: QPointF):
        """Add a new node of the given type at scene_pos (undoable)."""
        self._undo.push(AddNodeCommand(self, type_name, scene_pos))

    def clear(self, ask_user: bool = True):
        """Clear the entire editor (undoable), optionally asking the user for confirmation.

        Returns:
            bool: True if a clear operation was initiated.
        """
        if not self._alive or self.scene is None or self.view is None:
            return False
        if ask_user and self.on_clear and callable(self.on_clear):
            self.on_clear()
            return
        if ask_user:
            reply = QMessageBox.question(self, trans("agent.builder.confirm.clear.title"),
                                         trans("agent.builder.confirm.clear.msg"),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return False
        self._undo.push(ClearGraphCommand(self))
        return True

    def undo(self):
        """Undo last action."""
        self._undo.undo()

    def redo(self):
        """Redo last undone action."""
        self._undo.redo()

    def save_layout(self) -> dict:
        """Serialize the current layout into a compact, value-only dict.

        Notes:
            - Property specification (type, editable, allowed_inputs/outputs, etc.) is NOT exported.
            - Only dynamic, value-carrying properties are persisted.
            - Registry definitions are the single source of truth for property specs during load.
        """
        if not self._alive or self.scene is None or self.view is None:
            return False

        # Build compact graph payload (nodes + connections without specs)
        compact = self._serialize_layout_compact()

        # Positions and sizes come from live scene items
        compact["positions"] = {
            nuuid: [self._uuid_to_item[nuuid].pos().x(), self._uuid_to_item[nuuid].pos().y()]
            for nuuid in self._uuid_to_item
        }
        compact["sizes"] = {
            nuuid: [float(self._uuid_to_item[nuuid].size().width()),
                    float(self._uuid_to_item[nuuid].size().height())]
            for nuuid in self._uuid_to_item
        }

        # Persist the current view (zoom and scrollbars)
        try:
            compact["view"] = self._save_view_state()
        except Exception:
            compact["view"] = {}

        return compact

    def load_layout(self, data: dict):
        """
        Load layout using the live registry for node specs. Only values from the layout are applied,
        and only for properties that still exist in the current spec. Everything else falls back to
        the registry defaults. Connections are recreated only if ports still exist and can connect.
        """
        if not self._alive or self.scene is None or self.view is None:
            return False

        # Guard: mark layout import phase to avoid auto-renumbering of Base ID on nodeAdded.
        self._is_loading_layout = True
        try:
            self._dbg("load_layout -> registry-first import with value-only merge")
            # Reset interaction and clear both scene and graph (do not reuse graph.from_dict here).
            self._reset_interaction_states(remove_hidden_edges=True)
            self._clear_scene_only(hard=True)
            try:
                self.graph.clear(silent=True)
            except Exception:
                # Be defensive in case .clear is not available or raises
                self.graph.nodes = {}
                self.graph.connections = {}

            # Also reset per-layout Base ID counters; they will be rebuilt from the loaded data.
            self._reset_base_id_counters()

            # Extract normalized structures from possibly diverse layout shapes.
            nodes_norm, conns_norm, positions, sizes = self._normalize_layout_dict(data)

            # 1) Create nodes from registry spec, preserve UUID, set values that match current spec.
            created: Dict[str, NodeModel] = {}
            for nd in nodes_norm:
                tname = nd.get("type")
                nuuid = nd.get("uuid")
                if not tname or not nuuid:
                    self._dbg(f"load_layout: skip node without type/uuid: {nd}")
                    continue

                try:
                    node = self.graph.create_node_from_type(tname)
                except Exception as ex:
                    self._dbg(f"load_layout: create_node_from_type failed for '{tname}': {ex}")
                    continue

                # Preserve UUID and optional name from layout (if present).
                try:
                    node.uuid = nuuid
                except Exception:
                    pass
                name = nd.get("name")
                if isinstance(name, str) and name.strip():
                    try:
                        node.name = name
                    except Exception:
                        pass

                # Preserve friendly node.id from layout if present (keeps per-layout numbering).
                try:
                    fid = nd.get("id")
                    if isinstance(fid, str) and fid.strip():
                        node.id = fid.strip()
                except Exception:
                    pass

                # Apply property values only for properties that exist in the current spec.
                values_map: Dict[str, Any] = nd.get("values", {})
                for pid, pm in list(node.properties.items()):
                    if pid in values_map:
                        val = self._coerce_value_for_property(pm, values_map[pid])
                        try:
                            pm.value = val
                        except Exception:
                            pass

                # Schedule position (used in _on_graph_node_added) and add to graph.
                pos_xy = positions.get(nuuid)
                if isinstance(pos_xy, (list, tuple)) and len(pos_xy) == 2:
                    try:
                        self._pending_node_positions[nuuid] = QPointF(float(pos_xy[0]), float(pos_xy[1]))
                    except Exception:
                        pass
                self.graph.add_node(node)
                created[nuuid] = node

            # 2) Apply sizes after items exist.
            for nuuid, wh in sizes.items():
                item = self._uuid_to_item.get(nuuid)
                if item and isinstance(wh, (list, tuple)) and len(wh) == 2:
                    try:
                        w = float(wh[0]); h = float(wh[1])
                        item._apply_resize(QSizeF(w, h), clamp=True)
                    except Exception:
                        pass

            # 3) Recreate connections if possible.
            for cd in conns_norm:
                cuuid = cd.get("uuid")
                s_n = cd.get("src_node")
                s_p = cd.get("src_prop")
                d_n = cd.get("dst_node")
                d_p = cd.get("dst_prop")

                if not (s_n in created and d_n in created and isinstance(s_p, str) and isinstance(d_p, str)):
                    self._dbg(f"load_layout: skip connection with missing nodes/props: {cd}")
                    continue

                # Validate ports exist in current spec.
                if s_p not in created[s_n].properties or d_p not in created[d_n].properties:
                    self._dbg(f"load_layout: skip connection with non-existing port(s) in current spec: {cd}")
                    continue

                # Check if connection is allowed in current graph state.
                ok, reason = self.graph.can_connect((s_n, s_p), (d_n, d_p))
                if not ok:
                    self._dbg(f"load_layout: cannot connect ({s_n}.{s_p}) -> ({d_n}.{d_p}): {reason}")
                    continue

                # Try to preserve original connection UUID if available.
                conn_model = ConnectionModel(
                    uuid=cuuid if isinstance(cuuid, str) and cuuid else None,
                    src_node=s_n, src_prop=s_p,
                    dst_node=d_n, dst_prop=d_p
                )
                ok_add, reason_add = self.graph.add_connection(conn_model)
                if not ok_add:
                    # Fallback: let graph assign a fresh UUID (should rarely be needed).
                    ok2, reason2, _ = self.graph.connect((s_n, s_p), (d_n, d_p))
                    if not ok2:
                        self._dbg(f"load_layout: failed to add connection even via connect(): {reason_add} / {reason2}")

            # 4) Sync ports after all nodes/connections are in place.
            for item in self._uuid_to_item.values():
                if _qt_is_valid(item):
                    item.update_ports_positions()

            # Rebuild Base ID counters based on the just-loaded layout.
            self._rebuild_base_id_counters()

            self._reapply_stylesheets()
            self._update_status_label()

            # Restore view state if present; otherwise center on content (backward compatible).
            vs = self._extract_view_state(data)
            if vs:
                self._apply_view_state(vs)
            else:
                self.center_on_content()
            return True
        finally:
            # Always clear the loading flag even if exceptions happen during import.
            self._is_loading_layout = False

    def export_schema(self, as_list: bool = False) -> Union[dict, List[dict]]:
        """Export the graph schema (delegates to NodeGraph)."""
        if as_list:
            return self.graph.to_list_schema()
        return self.graph.to_schema()

    def debug_state(self) -> dict:
        """Return a diagnostics snapshot (same as save_layout)."""
        return self.save_layout()

    def zoom_in(self):
        """Zoom in the view."""
        if _qt_is_valid(self.view):
            self.view.zoom_in()

    def zoom_out(self):
        """Zoom out the view."""
        if _qt_is_valid(self.view):
            self.view.zoom_out()

    # ---------- Graph <-> UI sync ----------

    def _model_by_uuid(self, node_uuid: str) -> Optional[NodeModel]:
        """Return NodeModel by UUID from the graph."""
        return self.graph.nodes.get(node_uuid)

    def _on_graph_node_added(self, node: NodeModel):
        """Create a NodeItem when a NodeModel is added to the graph."""
        if node.uuid in self._uuid_to_item:
            return

        # Do not auto-increment Base ID here to avoid double steps.
        # Base ID assignment is handled at the command/model creation stage (e.g. AddNodeCommand).
        pos = self._pending_node_positions.pop(node.uuid, None)
        if pos is None:
            pos = self._next_spawn_pos()
        self._dbg(f"graph.nodeAdded -> add item for node={node.name}({node.uuid}) at {pos}")
        self._add_node_item(node, pos)

        # Keep Base ID counters in sync with newly added nodes.
        self._update_base_id_counters_from_node(node)
        self._update_status_label()

    def _on_graph_node_removed(self, node_uuid: str):
        """Remove the NodeItem when model is removed from the graph."""
        self._dbg(f"graph.nodeRemoved -> remove item for node={node_uuid}")
        item = self._uuid_to_item.pop(node_uuid, None)
        if item and _qt_is_valid(item):
            try:
                item.detach_proxy_widget()
            except Exception:
                pass
            try:
                self.scene.removeItem(item)
            except Exception:
                pass

        # Rebuild Base ID counters after removal to reflect current layout state.
        self._rebuild_base_id_counters()
        self._update_status_label()

    def _on_graph_connection_added(self, conn: ConnectionModel):
        """Create an EdgeItem when a ConnectionModel appears in the graph."""
        self._dbg(f"graph.connectionAdded -> add edge uuid={conn.uuid} src=({conn.src_node},{conn.src_prop}) dst=({conn.dst_node},{conn.dst_prop})")
        self._add_edge_for_connection(conn)

    def _on_graph_connection_removed(self, conn_uuid: str):
        """Remove the EdgeItem when a connection is removed from the graph."""
        self._dbg(f"graph.connectionRemoved -> remove edge uuid={conn_uuid}")
        edge = self._conn_uuid_to_edge.pop(conn_uuid, None)
        if edge:
            edge.src_port.increment_connections(-1)
            edge.dst_port.increment_connections(-1)
            if _qt_is_valid(edge.src_port.node_item):
                edge.src_port.node_item.remove_edge(edge)
            if _qt_is_valid(edge.dst_port.node_item):
                edge.dst_port.node_item.remove_edge(edge)
            if _qt_is_valid(edge):
                try:
                    self.scene.removeItem(edge)
                except Exception:
                    pass

    def _on_graph_cleared(self):
        """React to graph cleared by clearing the scene (items only)."""
        self._dbg("graph.cleared -> clear scene only")
        self._reset_interaction_states(remove_hidden_edges=True)
        self._clear_scene_only(hard=True)
        # Reset Base ID counters on clear so next layout starts fresh.
        self._reset_base_id_counters()
        self._update_status_label()

    # ---------- Scene helpers ----------

    def _scene_to_global(self, scene_pos: QPointF) -> QPoint:
        """Convert scene coordinates to a global screen QPoint."""
        # Correct mapping: scene -> viewport -> global
        vp_pt = self.view.mapFromScene(scene_pos)  # QPoint
        return self.view.viewport().mapToGlobal(vp_pt)

    def _on_scene_context_menu(self, scene_pos: QPointF):
        """Show context menu for adding nodes and undo/redo/clear at empty scene position."""
        # External permission check; when callable absent -> allowed
        try:
            allowed = True if self.editing_allowed is None else bool(self.editing_allowed())
        except Exception:
            allowed = False
        if not allowed:
            return

        menu = QMenu(self.window())
        ss = self.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)

        add_menu = menu.addMenu(self.config.menu_add())
        action_by_type: Dict[QAction, str] = {}
        for tname in self.graph.registry.types():
            act = add_menu.addAction(tname)
            action_by_type[act] = tname

        menu.addSeparator()
        act_undo = QAction(self.config.menu_undo(), menu)
        act_redo = QAction(self.config.menu_redo(), menu)
        act_clear = QAction(self.config.menu_clear(), menu)
        act_undo.setEnabled(self._undo.canUndo())
        act_redo.setEnabled(self._undo.canRedo())
        menu.addAction(act_undo)
        menu.addAction(act_redo)
        menu.addSeparator()
        menu.addAction(act_clear)

        global_pos = self._scene_to_global(scene_pos)
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == act_undo:
            self.undo()
        elif chosen == act_redo:
            self.redo()
        elif chosen == act_clear:
            self.clear(ask_user=True)
        elif chosen in action_by_type:
            type_name = action_by_type[chosen]
            self._undo.push(AddNodeCommand(self, type_name, scene_pos))

    # ---------- Z-order helpers ----------

    def raise_node_to_top(self, item: NodeItem):
        """Bring the given node item to the front (dynamic z-order).

        Uses a monotonic counter so every 'active' node stacks above the previous one.
        Safe to call from mouse/selection handlers.
        """
        if not _qt_is_valid(item):
            return
        if not getattr(self, "_alive", True) or getattr(self, "_closing", False):
            return
        try:
            # Keep _z_top consistent and monotonic
            self._z_top = float(self._z_top) if isinstance(self._z_top, (int, float)) else 2.0
        except Exception:
            self._z_top = 2.0
        try:
            cur = float(item.zValue())
            if cur > self._z_top:
                self._z_top = cur
        except Exception:
            pass
        try:
            self._z_top += 1.0
            item.setZValue(self._z_top)
        except Exception:
            pass

    # ---------- Add/remove nodes/edges ----------

    def _add_node_model(self, node: NodeModel, scene_pos: QPointF):
        """Schedule a new node's position and add the model to the graph."""
        self._pending_node_positions[node.uuid] = scene_pos
        self.graph.add_node(node)

    def _add_node_item(self, node: NodeModel, scene_pos: QPointF):
        """Create and place a NodeItem for the given NodeModel."""
        item = NodeItem(self, node)
        self.scene.addItem(item)

        # Place either at exact scene_pos (collisions disabled) or find nearest free spot
        if not bool(self.enable_collisions):
            pos = QPointF(scene_pos)
        else:
            pos = self._find_free_position(scene_pos, item.size())

        item.setPos(pos)
        item.update_ports_positions()
        # Ensure newest items are drawn above when collisions are disabled
        if not bool(self.enable_collisions):
            try:
                self._z_top = float(self._z_top) + 1.0
            except Exception:
                self._z_top = 3.0
            item.setZValue(self._z_top)

        # From now on it's safe for itemChange to touch the scene/edges
        item.mark_ready_for_scene_ops(True)

        self._uuid_to_item[node.uuid] = item
        self._apply_styles_to_content(item._content)

    def _find_free_position(self, desired: QPointF, size: QSizeF, step: int = 40, max_rings: int = 20) -> QPointF:
        """Find a non-overlapping position near 'desired' using a spiral search."""
        def rect_at(p: QPointF) -> QRectF:
            return QRectF(p.x(), p.y(), size.width(), size.height()).adjusted(1, 1, -1, -1)
        def collides(p: QPointF) -> bool:
            r = rect_at(p)
            for it in self.scene.items(r, Qt.IntersectsItemBoundingRect):
                if isinstance(it, NodeItem):
                    other = QRectF(it.scenePos().x(), it.scenePos().y(), it.size().width(), it.size().height()).adjusted(1,1,-1,-1)
                    if r.intersects(other):
                        return True
            return False

        if not collides(desired):
            return desired

        x = y = 0
        dx, dy = 1, 0
        segment_length = 1
        p = QPointF(desired)
        for ring in range(1, max_rings + 1):
            for _ in range(2):
                for _ in range(segment_length):
                    p = QPointF(desired.x() + x * step, desired.y() + y * step)
                    if not collides(p):
                        return p
                    x += dx; y += dy
                dx, dy = -dy, dx
            segment_length += 1
        return desired

    def _next_spawn_pos(self) -> QPointF:
        """Return next spawn position around cached origin (grid-based expansion)."""
        if self._spawn_origin is None:
            if not self.view.viewport().rect().isEmpty():
                self._spawn_origin = self.view.mapToScene(self.view.viewport().rect().center())
            else:
                self._spawn_origin = self.scene.sceneRect().center()
        origin = self._spawn_origin
        step = 80
        base_grid = [(-1, -1), (0, -1), (1, -1),
                     (-1,  0), (0,  0), (1,  0),
                     (-1,  1), (0,  1), (1, 1)]
        ring = self._spawn_index // len(base_grid) + 1
        gx, gy = base_grid[self._spawn_index % len(base_grid)]
        self._spawn_index += 1
        return QPointF(origin.x() + gx * step * ring, origin.y() + gy * step * ring)

    def _remove_node_by_uuid(self, node_uuid: str):
        """Remove a node model by UUID (graph will emit nodeRemoved)."""
        self.graph.remove_node(node_uuid)

    def _add_edge_for_connection(self, conn: ConnectionModel):
        """Create an EdgeItem in the scene for a given ConnectionModel."""
        ex = self._conn_uuid_to_edge.get(conn.uuid)
        if ex and _qt_is_valid(ex):
            self._dbg(f"_add_edge_for_connection: guard skip duplicate for uuid={conn.uuid}")
            return

        src_item = self._uuid_to_item.get(conn.src_node)
        dst_item = self._uuid_to_item.get(conn.dst_node)
        if not src_item or not dst_item:
            self._dbg(f"_add_edge_for_connection: missing node items for conn={conn.uuid}")
            return
        src_port = src_item._out_ports.get(conn.src_prop)
        dst_port = dst_item._in_ports.get(conn.dst_prop)
        if not src_port or not dst_port:
            self._dbg(f"_add_edge_for_connection: missing ports src={bool(src_port)} dst={bool(dst_port)}")
            return
        edge = EdgeItem(src_port, dst_port, temporary=False)
        edge.update_path()
        self.scene.addItem(edge)
        src_item.add_edge(edge)
        dst_item.add_edge(edge)
        src_port.increment_connections(+1)
        dst_port.increment_connections(+1)
        edge._conn_uuid = conn.uuid
        self._conn_uuid_to_edge[conn.uuid] = edge
        self._dbg(f"_add_edge_for_connection: edge id={id(edge)} mapped to uuid={conn.uuid}")

    def _remove_connection_by_uuid(self, conn_uuid: str):
        """Remove a connection by UUID (graph will emit connectionRemoved)."""
        self._dbg(f"_remove_connection_by_uuid -> {conn_uuid}")
        self.graph.remove_connection(conn_uuid)

    # ---------- Theming helpers ----------

    def _update_theme(self):
        """Refresh colors, pens, and re-apply styles to content widgets."""
        if not getattr(self, "_alive", True):
            return
        if getattr(self, "_closing", False):
            return
        if getattr(self, "view", None) is None:
            return
        self._dbg("_update_theme")
        for item in self._uuid_to_item.values():
            if _qt_is_valid(item):
                item._apply_resize(item.size(), clamp=True)
                item.update()
                for p in list(item._in_ports.values()) + list(item._out_ports.values()):
                    if _qt_is_valid(p):
                        p.notify_theme_changed()
        for edge in self._conn_uuid_to_edge.values():
            if _qt_is_valid(edge):
                edge._update_pen()
                edge.update()
        if _qt_is_valid(self.view):
            self.view.viewport().update()
        self._reapply_stylesheets()

    def _current_stylesheet(self) -> str:
        """Return the active stylesheet from window or QApplication."""
        wnd = self.window()
        if isinstance(wnd, QWidget) and wnd.styleSheet():
            return wnd.styleSheet()
        if QApplication.instance() and QApplication.instance().styleSheet():
            return QApplication.instance().styleSheet()
        return ""

    def _current_palette(self) -> QPalette:
        """Return the active palette from window or QApplication."""
        wnd = self.window()
        if isinstance(wnd, QWidget):
            return wnd.palette()
        return QApplication.instance().palette() if QApplication.instance() else self.palette()

    def _current_font(self) -> QFont:
        """Return the active application/widget font to keep NodeEditor consistent with the app."""
        wnd = self.window()
        if isinstance(wnd, QWidget):
            return wnd.font()
        app = QApplication.instance()
        if app:
            return app.font()
        return self.font()

    def _apply_styles_to_content(self, content_widget: QWidget):
        """Propagate palette, font and stylesheet to the embedded content widget subtree."""
        if content_widget is None:
            return
        content_widget.setAttribute(Qt.WA_StyledBackground, True)
        stylesheet = self._current_stylesheet()
        pal = self._current_palette()
        font = self._current_font()
        content_widget.setPalette(pal)
        content_widget.setFont(font)
        if stylesheet:
            content_widget.setStyleSheet(stylesheet)
        content_widget.ensurePolished()
        for w in content_widget.findChildren(QWidget):
            w.setPalette(pal)
            w.setFont(font)
            if stylesheet:
                w.setStyleSheet(stylesheet)
            w.ensurePolished()

    def _reapply_stylesheets(self):
        """Reapply palette, font and stylesheet to all NodeContentWidget instances."""
        if not getattr(self, "_alive", True) or getattr(self, "_closing", False):
            return
        stylesheet = self._current_stylesheet()
        pal = self._current_palette()
        font = self._current_font()
        for item in self._uuid_to_item.values():
            if item._content and _qt_is_valid(item._content):
                item._content.setPalette(pal)
                item._content.setFont(font)
                if stylesheet:
                    item._content.setStyleSheet(stylesheet)
                item._content.ensurePolished()
                for w in item._content.findChildren(QWidget):
                    w.setPalette(pal)
                    w.setFont(font)
                    if stylesheet:
                        w.setStyleSheet(stylesheet)
                    w.ensurePolished()

    # ---------- Edge/Port helpers + rewire ----------

    def _edges_for_port(self, port: PortItem) -> List[EdgeItem]:
        """Return all persistent edges currently attached to a port."""
        res: List[EdgeItem] = []
        nitem = port.node_item
        for e in list(nitem._edges):
            if _qt_is_valid(e) and not e.temporary and (e.src_port is port or e.dst_port is port):
                res.append(e)
        for it in self.scene.items():
            if isinstance(it, EdgeItem) and not it.temporary and (it.src_port is port or it.dst_port is port):
                if it not in res:
                    res.append(it)
        self._dbg(f"_edges_for_port: port={port.prop_id}/{port.side} -> {len(res)} edges")
        return res

    def _port_has_connections(self, port: PortItem) -> bool:
        """Return True if the port has any attached edges (fast path + scene scan)."""
        res = (getattr(port, "_connected_count", 0) > 0) or bool(self._edges_for_port(port))
        self._dbg(f"_port_has_connections: port={port.prop_id}/{port.side} -> {res}")
        return res

    def _choose_edge_near_cursor(self, edges: List[EdgeItem], cursor_scene: QPointF, ref_port: PortItem) -> Optional[EdgeItem]:
        """Pick the edge whose 'other end' is closest to the cursor (ties broken by distance)."""
        if not edges:
            return None
        if len(edges) == 1:
            return edges[0]
        best = None
        best_d2 = float("inf")
        for e in edges:
            other = e.dst_port if e.src_port is ref_port else e.src_port
            op = other.scenePos()
            dx = cursor_scene.x() - op.x()
            dy = cursor_scene.y() - op.y()
            d2 = dx*dx + dy*dy
            if d2 < best_d2:
                best_d2 = d2
                best = e
        return best

    def _allowed_from_spec(self, node: NodeModel, pid: str) -> Tuple[int, int]:
        """Return (allowed_outputs, allowed_inputs) for a property ID using registry or model."""
        out_allowed = 0
        in_allowed = 0
        try:
            tp = node.type
            spec_type = self.graph.registry.get(tp) if self.graph and self.graph.registry else None
            prop_obj = None
            if spec_type is not None:
                for attr in ("properties", "props", "fields", "ports", "inputs", "outputs"):
                    try:
                        cont = getattr(spec_type, attr, None)
                        if isinstance(cont, dict) and pid in cont:
                            prop_obj = cont[pid]
                            break
                    except Exception:
                        pass
                if prop_obj is None:
                    for meth in ("get_property", "property_spec", "get_prop", "prop", "property"):
                        if hasattr(spec_type, meth):
                            try:
                                prop_obj = getattr(spec_type, meth)(pid)
                                break
                            except Exception:
                                pass
            def _get_int(o, k, default=0):
                try:
                    v = getattr(o, k, None)
                    if isinstance(v, int):
                        return v
                except Exception:
                    pass
                try:
                    if isinstance(o, dict):
                        v = o.get(k)
                        if isinstance(v, int):
                            return v
                except Exception:
                    pass
                return default
            if prop_obj is not None:
                out_allowed = _get_int(prop_obj, "allowed_outputs", 0)
                in_allowed = _get_int(prop_obj, "allowed_inputs", 0)
            else:
                pm = node.properties.get(pid)
                if pm:
                    out_allowed = int(getattr(pm, "allowed_outputs", 0))
                    in_allowed = int(getattr(pm, "allowed_inputs", 0))
        except Exception:
            pm = node.properties.get(pid)
            if pm:
                out_allowed = int(getattr(pm, "allowed_outputs", 0))
                in_allowed = int(getattr(pm, "allowed_inputs", 0))
        return out_allowed, in_allowed

    def _can_connect_during_rewire(self, src: PortItem, dst: PortItem) -> bool:
        """Lightweight, allocation-free check to validate a rewire candidate."""
        try:
            src_node = self.graph.nodes.get(src.node_item.node.uuid)
            dst_node = self.graph.nodes.get(dst.node_item.node.uuid)
            if not src_node or not dst_node:
                return False
            sp = src_node.properties.get(src.prop_id)
            dp = dst_node.properties.get(dst.prop_id)
            if not sp or not dp:
                return False
            if sp.type != dp.type:
                return False
            sp_out_allowed, _ = self._allowed_from_spec(src_node, src.prop_id)
            _, dp_in_allowed = self._allowed_from_spec(dst_node, dst.prop_id)
            skip_uuid = self._rewire_conn_uuid
            src_count = sum(1 for c in self.graph.connections.values()
                            if c.src_node == src.node_item.node.uuid and c.src_prop == src.prop_id and c.uuid != skip_uuid)
            dst_count = sum(1 for c in self.graph.connections.values()
                            if c.dst_node == dst.node_item.node.uuid and c.dst_prop == dst.prop_id and c.uuid != skip_uuid)
            if isinstance(sp_out_allowed, int) and sp_out_allowed > 0 and src_count >= sp_out_allowed:
                return False
            if isinstance(dp_in_allowed, int) and dp_in_allowed > 0 and dst_count >= dp_in_allowed:
                return False
            return True
        except Exception:
            return False

    def _can_connect_for_interaction(self, src: PortItem, dst: PortItem) -> bool:
        """Check whether src -> dst would be allowed, considering current interaction mode."""
        if self._wire_state in ("rewiring", "rewire-primed"):
            return self._can_connect_during_rewire(src, dst)
        ok, _ = self.graph.can_connect((src.node_item.node.uuid, src.prop_id),
                                       (dst.node_item.node.uuid, dst.prop_id))
        return ok

    def _find_compatible_port_at(self, scene_pos: QPointF, radius: Optional[float] = None) -> Optional[PortItem]:
        """Find nearest compatible port to scene_pos when dragging an interactive wire."""
        if self._interactive_src_port is None:
            return None
        src = self._interactive_src_port
        pick_r_cfg = float(getattr(self, "_port_pick_radius", 10.0) or 10.0)
        pick_r = float(radius) if radius is not None else max(18.0, pick_r_cfg + 10.0)
        rect = QRectF(scene_pos.x() - pick_r, scene_pos.y() - pick_r, 2 * pick_r, 2 * pick_r) if False else QRectF(scene_pos.x() - pick_r, scene_pos.y() - pick_r, 2 * pick_r, 2 * pick_r)
        items = self.scene.items(rect, Qt.IntersectsItemShape, Qt.DescendingOrder, self.view.transform())
        best: Optional[PortItem] = None
        best_d2 = float("inf")
        for it in items:
            if not isinstance(it, PortItem) or it is src:
                continue
            a, b = self._resolve_direction(src, it)
            if not a or not b:
                continue
            if a.node_item.node.uuid == b.node_item.node.uuid:
                continue
            if not self._can_connect_for_interaction(a, b):
                continue
            pp = it.scenePos()
            dx = scene_pos.x() - pp.x()
            dy = scene_pos.y() - pp.y()
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                best = it
        if best:
            self._dbg(f"_find_compatible_port_at: FOUND port={best.prop_id}/{best.side} on node={best.node_item.node.name}")
        return best

    def _enter_wire_drag_mode(self):
        """Temporarily disable view drag to ensure smooth wire interaction."""
        try:
            self._saved_drag_mode = self.view.dragMode()
            self.view.setDragMode(QGraphicsView.NoDrag)
        except Exception:
            self._saved_drag_mode = None

    def _leave_wire_drag_mode(self):
        """Restore the view drag mode after wire interaction finishes."""
        if self._saved_drag_mode is not None and _qt_is_valid(self.view):
            try:
                self.view.setDragMode(self._saved_drag_mode)
            except Exception:
                pass
        self._saved_drag_mode = None

    def _on_port_clicked(self, port: PortItem):
        """Start drawing a new wire or prime a rewire depending on modifiers and port state.

        Behavior:
            - Click: start a new connection from the clicked port.
            - Ctrl+Click on a connected port: prime rewire/detach, selecting the closest edge.
        """
        self._dbg(f"_on_port_clicked: side={port.side}, prop={port.prop_id}, connected={self._port_has_connections(port)}")
        mods = QApplication.keyboardModifiers()
        # Ctrl+click on a connected port enters rewire/detach mode; plain click always starts a new connection
        rewire_requested = bool(mods & Qt.ControlModifier)
        if rewire_requested and self._port_has_connections(port):
            cursor_scene = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
            edges = self._edges_for_port(port)
            edge = self._choose_edge_near_cursor(edges, cursor_scene, port)
            if edge:
                self._prime_rewire_from_conn(port, getattr(edge, "_conn_uuid", None), edge, cursor_scene)
                return
        self._start_draw(port)

    def _prime_rewire_from_conn(self, origin_port: PortItem, conn_uuid: Optional[str],
                                edge: Optional[EdgeItem], press_scene_pos: QPointF):
        """Prime the 'rewire' state from an existing connection without moving yet.

        This state transitions into actual rewiring when the cursor moves beyond a small threshold.
        """
        if self._wire_state != "idle":
            return
        self._wire_state = "rewire-primed"
        self._rewire_conn_uuid = conn_uuid
        self._rewire_hidden_edge = edge
        fixed_src = origin_port if origin_port.side == "output" else (edge.src_port if edge else None)
        if fixed_src is None:
            self._wire_state = "idle"
            self._rewire_conn_uuid = None
            self._rewire_hidden_edge = None
            return
        self._rewire_fixed_src = fixed_src
        self._interactive_src_port = fixed_src
        self._rewire_press_scene_pos = QPointF(press_scene_pos)

    def _start_draw(self, src_port: PortItem):
        """Begin interactive wire drawing from a source port."""
        if self._wire_state != "idle":
            return
        self._wire_state = "drawing"
        self._interactive_src_port = src_port
        self._interactive_edge = EdgeItem(src_port=src_port, dst_port=src_port, temporary=True)
        self.scene.addItem(self._interactive_edge)
        self._interactive_edge.update_path(src_port.scenePos())
        self._enter_wire_drag_mode()

    def _start_rewire_from_edge(self, edge: EdgeItem, cursor_scene_pos: QPointF):
        """Start rewiring by hiding the original edge and creating a temporary wire."""
        if self._wire_state != "idle" or not _qt_is_valid(edge):
            return
        self._wire_state = "rewiring"
        self._rewire_hidden_edge = edge
        self._rewire_conn_uuid = getattr(edge, "_conn_uuid", None)
        self._rewire_fixed_src = edge.src_port
        self._interactive_src_port = edge.src_port
        edge.setVisible(False)
        self._interactive_edge = EdgeItem(src_port=edge.src_port, dst_port=edge.src_port, temporary=True)
        self.scene.addItem(self._interactive_edge)
        self._interactive_edge.update_path(end_pos=cursor_scene_pos)
        self._enter_wire_drag_mode()

    def _resolve_direction(self, a: PortItem, b: PortItem) -> Tuple[Optional[PortItem], Optional[PortItem]]:
        """Return (src, dst) if ports are complementary, otherwise (None, None)."""
        if a.side == "output" and b.side == "input":
            return a, b
        if a.side == "input" and b.side == "output":
            return b, a
        return None, None

    def _set_hover_candidate(self, port: Optional[PortItem]):
        """Highlight/unhighlight the current hover-accept candidate port."""
        if self._hover_candidate is port:
            return
        if self._hover_candidate is not None and _qt_is_valid(self._hover_candidate):
            self._hover_candidate.set_accept_highlight(False)
        self._hover_candidate = port
        if self._hover_candidate is not None and _qt_is_valid(self._hover_candidate):
            self._hover_candidate.set_accept_highlight(True)

    def eventFilter(self, obj, event):
        """Intercept scene mouse events to implement interactive wiring and rewiring."""
        if not self._alive or self.scene is None or self.view is None:
            return False
        if obj is self.scene:
            et = event.type()

            # Rewire: convert primed state into actual rewiring after small cursor movement.
            if self._wire_state == "rewire-primed" and et == QEvent.GraphicsSceneMouseMove:
                pos = event.scenePos()
                if self._rewire_press_scene_pos is not None:
                    dist = abs(pos.x() - self._rewire_press_scene_pos.x()) + abs(pos.y() - self._rewire_press_scene_pos.y())
                else:
                    dist = 9999
                if dist > 6 and self._rewire_fixed_src is not None:
                    if self._rewire_hidden_edge and _qt_is_valid(self._rewire_hidden_edge):
                        self._rewire_hidden_edge.setVisible(False)
                    self._interactive_edge = EdgeItem(src_port=self._rewire_fixed_src, dst_port=self._rewire_fixed_src, temporary=True)
                    self.scene.addItem(self._interactive_edge)
                    self._interactive_edge.update_path(end_pos=pos)
                    self._enter_wire_drag_mode()
                    self._wire_state = "rewiring"
                    candidate = self._find_compatible_port_at(pos, radius=28.0)
                    self._set_hover_candidate(candidate)
                    return True

            # While dragging a wire, update temporary path and hover highlight.
            if self._interactive_edge is not None and et == QEvent.GraphicsSceneMouseMove:
                pos = event.scenePos()
                if _qt_is_valid(self._interactive_edge):
                    self._interactive_edge.update_path(end_pos=pos)
                candidate = self._find_compatible_port_at(pos, radius=28.0)
                self._set_hover_candidate(candidate)
                return True

            # RMB cancels interactive connection (drawing or rewiring).
            if self._interactive_edge is not None and et == QEvent.GraphicsSceneMousePress and event.button() == Qt.RightButton:
                self._cancel_interactive_connection()
                return True

            # LMB release: finalize interactive connection or rewire.
            if et == QEvent.GraphicsSceneMouseRelease and event.button() == Qt.LeftButton:
                if self._wire_state == "rewire-primed":
                    self._finish_interactive_connection()
                    return True

                if self._interactive_edge is not None:
                    pos = event.scenePos()
                    target = self._find_compatible_port_at(pos, radius=48.0)
                    if target is None and self._hover_candidate is not None:
                        target = self._hover_candidate

                    if self._wire_state == "rewiring":
                        if isinstance(target, PortItem) and self._rewire_fixed_src is not None:
                            src, dst = self._resolve_direction(self._rewire_fixed_src, target)
                            if src and dst:
                                if self._rewire_conn_uuid and self._rewire_conn_uuid in self.graph.connections:
                                    old = self.graph.connections.get(self._rewire_conn_uuid)
                                    if old:
                                        self._undo.push(RewireConnectionCommand(self, old, src, dst))
                                else:
                                    self._undo.push(ConnectCommand(self, src, dst))
                                    if self._rewire_hidden_edge:
                                        self._detach_edge_item(self._rewire_hidden_edge)
                        else:
                            # Drop on empty space: delete or detach depending on availability.
                            if self._rewire_conn_uuid and self._rewire_conn_uuid in self.graph.connections:
                                old = self.graph.connections.get(self._rewire_conn_uuid)
                                if old:
                                    self._undo.push(RewireConnectionCommand(self, old, None, None))
                            elif self._rewire_hidden_edge:
                                self._delete_edge(self._rewire_hidden_edge)
                        self._finish_interactive_connection()
                        return True

                    elif self._wire_state == "drawing":
                        if isinstance(target, PortItem) and self._interactive_src_port is not None:
                            src, dst = self._resolve_direction(self._interactive_src_port, target)
                            if src and dst:
                                self._undo.push(ConnectCommand(self, src, dst))
                        self._finish_interactive_connection()
                        return True

        return super().eventFilter(obj, event)

    def _reset_interaction_states(self, remove_hidden_edges: bool):
        """Reset all interactive wiring state and optionally remove hidden edges."""
        self._set_hover_candidate(None)
        if self._interactive_edge and _qt_is_valid(self._interactive_edge):
            try:
                self.scene.removeItem(self._interactive_edge)
            except Exception:
                pass
        self._interactive_edge = None
        self._interactive_src_port = None

        if remove_hidden_edges and self._rewire_hidden_edge and _qt_is_valid(self._rewire_hidden_edge):
            try:
                self.scene.removeItem(self._rewire_hidden_edge)
            except Exception:
                pass
        elif self._rewire_hidden_edge and _qt_is_valid(self._rewire_hidden_edge):
            if self._rewire_hidden_edge.scene() is not None:
                self._rewire_hidden_edge.setVisible(True)

        self._wire_state = "idle"
        self._rewire_conn_uuid = None
        self._rewire_hidden_edge = None
        self._rewire_fixed_src = None
        self._rewire_press_scene_pos = None
        self._leave_wire_drag_mode()

    def _finish_interactive_connection(self):
        """Finish interactive connection/rewire and restore view drag mode."""
        self._reset_interaction_states(remove_hidden_edges=False)

    def _cancel_interactive_connection(self):
        """Cancel interactive connection/rewire."""
        self._reset_interaction_states(remove_hidden_edges=False)

    # ---------- Delete helpers ----------

    def _on_delete_shortcut(self):
        """Delete selected nodes and/or connections unless a text input is focused (undoable)."""
        if self._is_text_input_focused():
            self._dbg("Delete ignored: text input is focused")
            return
        if not _qt_is_valid(self.scene):
            return

        selected = list(self.scene.selectedItems())
        if not selected:
            return

        nodes = [it for it in selected if isinstance(it, NodeItem)]
        edges = [it for it in selected if isinstance(it, EdgeItem)]

        # Filter out edges that are attached to nodes being deleted; they will be handled by the node command.
        if nodes and edges:
            node_uuids = {n.node.uuid for n in nodes}
            edges = [
                e for e in edges
                if _qt_is_valid(e.src_port) and _qt_is_valid(e.dst_port) and
                   e.src_port.node_item.node.uuid not in node_uuids and
                   e.dst_port.node_item.node.uuid not in node_uuids
            ]

        if not nodes and not edges:
            return

        self._dbg(f"Delete shortcut -> nodes={len(nodes)}, edges={len(edges)} (undoable)")
        self._undo.beginMacro(self.config.macro_delete_selection())
        try:
            for n in nodes:
                # Push per-node undoable deletion (restores its own connections)
                self._delete_node_item(n)
            for e in edges:
                self._delete_edge_undoable(e)
        finally:
            self._undo.endMacro()

    def _delete_node_item(self, item: "NodeItem"):
        """Delete a node via undoable command."""
        try:
            if _qt_is_valid(item):
                self._dbg(f"_delete_node_item (undoable) -> node={item.node.uuid}")
                self._undo.push(DeleteNodeCommand(self, item))
        except Exception:
            pass

    def _detach_edge_item(self, edge: EdgeItem):
        """Detach an edge item from scene and internal maps without touching the graph."""
        try:
            edge.src_port.increment_connections(-1)
            edge.dst_port.increment_connections(-1)
        except Exception:
            pass
        if _qt_is_valid(edge.src_port.node_item):
            edge.src_port.node_item.remove_edge(edge)
        if _qt_is_valid(edge.dst_port.node_item):
            edge.dst_port.node_item.remove_edge(edge)
        for k, v in list(self._conn_uuid_to_edge.items()):
            if v is edge:
                self._conn_uuid_to_edge.pop(k, None)
        if _qt_is_valid(edge):
            try:
                self.scene.removeItem(edge)
            except Exception:
                pass

    def _delete_edge(self, edge: EdgeItem):
        """Delete an edge either by graph UUID or by detaching the item if orphan."""
        conn_uuid = getattr(edge, "_conn_uuid", None)
        exists = bool(conn_uuid and conn_uuid in self.graph.connections)
        if exists:
            self._remove_connection_by_uuid(conn_uuid)
        else:
            self._detach_edge_item(edge)

    def _delete_selected_connections(self):
        """Delete all currently selected edges in the scene (undoable)."""
        if not _qt_is_valid(self.scene):
            return
        for it in list(self.scene.selectedItems()):
            if isinstance(it, EdgeItem):
                self._delete_edge_undoable(it)
        if _qt_is_valid(self.view):
            self.view.viewport().update()

    def _delete_edge_undoable(self, edge: EdgeItem):
        """Delete a connection through the undo stack; fallback to immediate detach for orphans."""
        conn_uuid = getattr(edge, "_conn_uuid", None)
        if conn_uuid and conn_uuid in self.graph.connections:
            conn = self.graph.connections[conn_uuid]
            self._undo.push(DeleteConnectionCommand(self, conn))
        else:
            # Orphan/temporary edge: remove immediately (not tracked in the graph)
            self._delete_edge(edge)

    # ---------- Clear helpers ----------

    def _remove_all_edge_items_from_scene(self):
        """Remove every EdgeItem from the scene (used during teardown)."""
        if not _qt_is_valid(self.scene):
            return
        for it in list(self.scene.items()):
            if isinstance(it, EdgeItem):
                try:
                    self.scene.removeItem(it)
                except Exception:
                    pass

    def _cleanup_node_proxies(self):
        """Detach and delete QWidget proxies inside all NodeItems to prevent leaks."""
        for item in list(self._uuid_to_item.values()):
            try:
                if _qt_is_valid(item):
                    # Break edges/ports and disconnect signals before tearing down widgets/proxies
                    try:
                        item.pre_cleanup()
                    except Exception:
                        pass
                    item.detach_proxy_widget()
            except Exception:
                pass

    def _clear_scene_only(self, hard: bool = False):
        """Clear all NodeItems and EdgeItems from the scene (graph untouched unless caller decides)."""
        self._cleanup_node_proxies()
        for edge in list(self._conn_uuid_to_edge.values()):
            if _qt_is_valid(edge):
                try:
                    self.scene.removeItem(edge)
                except Exception:
                    pass
        self._conn_uuid_to_edge.clear()
        for item in list(self._uuid_to_item.values()):
            if _qt_is_valid(item):
                try:
                    # Ensure references are broken even if proxies were not detached earlier
                    try:
                        item.pre_cleanup()
                    except Exception:
                        pass
                    self.scene.removeItem(item)
                except Exception:
                    pass
        self._uuid_to_item.clear()
        if hard:
            self._remove_all_edge_items_from_scene()

    def _clear_scene_and_graph(self):
        """Clear both the scene items and the graph models."""
        self._reset_interaction_states(remove_hidden_edges=True)
        self._clear_scene_only(hard=True)
        self.graph.clear(silent=True)

    # ---------- Base ID auto-increment ----------

    def _is_base_id_pid(self, pid: str, pm: PropertyModel) -> bool:
        """Detect base-id-like property ids/names or explicit flag on the PropertyModel."""
        try:
            if getattr(pm, "is_base_id", False):
                return True
        except Exception:
            pass
        pid_key = (pid or "").strip().lower().replace(" ", "_")
        name_key = ""
        try:
            name_key = (pm.name or "").strip().lower().replace(" ", "_")
        except Exception:
            pass
        candidates = {"base_id", "baseid", "base", "id_base", "basename", "base_name"}
        return pid_key in candidates or name_key in candidates

    def _split_base_suffix(self, text: str) -> Tuple[str, Optional[int]]:
        """Split 'name_12' into ('name', 12). If no numeric suffix, return (text, None)."""
        if not isinstance(text, str):
            text = f"{text}"
        parts = text.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
        return text, None

    def _reset_base_id_counters(self):
        """Reset per-layout counters for Base ID suffixes."""
        self._base_id_max = {}

    def _bump_base_counter(self, prop_id: str, base: str, suffix: int):
        """Ensure the internal counter for (prop_id, base) is at least suffix."""
        try:
            d = self._base_id_max.setdefault(prop_id, {})
            cur = int(d.get(base, 0))
            if int(suffix) > cur:
                d[base] = int(suffix)
        except Exception:
            pass

    def _current_max_suffix_in_graph(self, prop_id: str, base: str) -> int:
        """Scan the current graph and return the highest numeric suffix used for given (prop_id, base).
        This guards against stale in-memory counters when switching layouts without a hard reset."""
        max_suf = 0
        try:
            if not base:
                return 0
            for node in self.graph.nodes.values():
                pm = node.properties.get(prop_id)
                if not pm:
                    continue
                raw = "" if pm.value is None else str(pm.value)
                b, suf = self._split_base_suffix(raw)
                if b == base and isinstance(suf, int):
                    if suf > max_suf:
                        max_suf = suf
        except Exception:
            return max_suf
        return max_suf

    def _next_suffix_for_base(self, prop_id: str, base: str) -> int:
        """Return next suffix to use for a given (prop_id, base) scoped to the current layout.
        Always computes from the live graph to avoid stale counters leaking between layouts."""
        try:
            actual_max = self._current_max_suffix_in_graph(prop_id, base)
            # Keep internal cache in sync with the observed state
            self._bump_base_counter(prop_id, base, actual_max)
            return max(1, actual_max + 1)
        except Exception:
            return 1

    def _update_base_id_counters_from_node(self, node: NodeModel):
        """Update counters using values from a single node."""
        try:
            for pid, pm in node.properties.items():
                if not self._is_base_id_pid(pid, pm):
                    continue
                raw = "" if pm.value is None else str(pm.value)
                base, suf = self._split_base_suffix(raw)
                if base is None or base == "":
                    continue
                if suf is None:
                    # At least register the base with suffix 0
                    self._bump_base_counter(pid, base, 0)
                else:
                    self._bump_base_counter(pid, base, int(suf))
        except Exception:
            pass

    def _rebuild_base_id_counters(self):
        """Recompute Base ID counters by scanning the current graph."""
        self._reset_base_id_counters()
        try:
            for node in self.graph.nodes.values():
                self._update_base_id_counters_from_node(node)
        except Exception:
            pass

    def _prepare_new_node_defaults(self, node: NodeModel):
        """When adding a node, auto-increment Base ID to keep uniqueness within the layout.

        Behavior for interactive add (not during load):
            - Detect base-id-like property.
            - Ignore any numeric suffix already present in the default.
            - Always assign base_{next_local_suffix}, where 'next' is computed from per-layout counters.
        """
        try:
            base_pid = None
            for pid, pm in node.properties.items():
                if self._is_base_id_pid(pid, pm):
                    base_pid = pid
                    break
            if not base_pid:
                return

            pm = node.properties.get(base_pid)
            if not pm:
                return

            raw = "" if pm.value is None else str(pm.value)
            base, _ = self._split_base_suffix(raw)
            if not base:
                # Do not generate suffix if base is empty
                return

            next_suf = self._next_suffix_for_base(base_pid, base)
            pm.value = f"{base}_{next_suf}"
            self._bump_base_counter(base_pid, base, next_suf)
        except Exception:
            pass

    # ---------- View centering ----------

    def content_bounding_rect(self) -> Optional[QRectF]:
        """Return the bounding rect of all nodes (in scene coords), or None if empty."""
        rect: Optional[QRectF] = None
        for item in self._uuid_to_item.values():
            r = item.mapToScene(item.boundingRect()).boundingRect()
            rect = r if rect is None else rect.united(r)
        return rect

    def center_on_content(self, margin: float = 80.0):
        """Center the view on all content, expanding scene rect with a safety margin."""
        rect = self.content_bounding_rect()
        if rect and rect.isValid():
            padded = rect.adjusted(-margin, -margin, margin, margin)
            self.scene.setSceneRect(self.scene.sceneRect().united(padded))
            self.view.centerOn(rect.center())

    def _save_view_state(self) -> dict:
        """Return a serializable snapshot of the current view (zoom and scrollbars)."""
        if not _qt_is_valid(self.view):
            return {}
        try:
            return self.view.view_state()
        except Exception:
            # Fallback in case view_state() is not available
            try:
                return {
                    "zoom": float(getattr(self.view, "_zoom", 1.0)),
                    "h": int(self.view.horizontalScrollBar().value()),
                    "v": int(self.view.verticalScrollBar().value()),
                }
            except Exception:
                return {}

    def _apply_view_state(self, state: dict):
        """Apply a previously saved view state to the graphics view."""
        if not _qt_is_valid(self.view) or not isinstance(state, dict):
            return
        try:
            self.view.set_view_state(state)
        except Exception:
            # Fallback path maintaining compatibility with minimal attributes
            try:
                z = state.get("zoom") or state.get("scale")
                if z is not None:
                    self.view.resetTransform()
                    self.view._zoom = 1.0
                    z = max(self.view._min_zoom, min(self.view._max_zoom, float(z)))
                    if abs(z - 1.0) > 1e-9:
                        self.view.scale(z, z)
                        self.view._zoom = z
                if state.get("h") is not None:
                    self.view.horizontalScrollBar().setValue(int(state["h"]))
                if state.get("v") is not None:
                    self.view.verticalScrollBar().setValue(int(state["v"]))
            except Exception:
                pass

    def _extract_view_state(self, data: dict) -> Optional[dict]:
        """Extract a view state from various possible blocks in layout data."""
        if not isinstance(data, dict):
            return None
        vs = None
        for key in ("view", "viewport", "camera", "view_state", "viewState"):
            blk = data.get(key)
            if isinstance(blk, dict):
                vs = blk
                break
        if vs is None:
            # Optional nested blocks
            for parent in ("meta", "ui"):
                blk = data.get(parent)
                if isinstance(blk, dict):
                    for key in ("view", "viewport", "camera", "view_state", "viewState"):
                        if isinstance(blk.get(key), dict):
                            vs = blk.get(key)
                            break
                if vs is not None:
                    break
        if not isinstance(vs, dict):
            return None
        out = {}
        z = vs.get("zoom") or vs.get("scale") or vs.get("z")
        h = vs.get("h") or vs.get("hScroll") or vs.get("scrollH") or vs.get("x")
        v = vs.get("v") or vs.get("vScroll") or vs.get("scrollV") or vs.get("y")
        try:
            if z is not None:
                out["zoom"] = float(z)
        except Exception:
            pass
        try:
            if h is not None:
                out["h"] = int(h)
        except Exception:
            pass
        try:
            if v is not None:
                out["v"] = int(v)
        except Exception:
            pass
        return out if out else None

    # ---------- Layout normalization helpers (registry-first import) ----------

    def _coerce_value_for_property(self, pm: PropertyModel, value: Any) -> Any:
        """Cast persisted value to the property's current type. Be permissive and safe.

        Supported types:
            - int, float, bool, combo (str), str, text
        All other/custom types are returned unchanged.
        """
        t = getattr(pm, "type", None)
        try:
            if t == "int":
                return int(value)
            if t == "float":
                return float(value)
            if t == "bool":
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    return bool(value)
                if isinstance(value, str):
                    lv = value.strip().lower()
                    if lv in ("1", "true", "yes", "y", "on"):
                        return True
                    if lv in ("0", "false", "no", "n", "off"):
                        return False
                return bool(value)
            if t == "combo":
                # Keep as string; actual validation against options happens in UI.
                return str(value)
            if t in ("str", "text"):
                return "" if value is None else str(value)
            # For custom types like "flow", "memory" we keep the raw value (usually None or id).
            return value
        except Exception:
            return value

    def _normalize_layout_dict(self, data: dict) -> Tuple[List[dict], List[dict], Dict[str, Tuple[float, float]], Dict[str, Tuple[float, float]]]:
        """
        Normalize various layout shapes into:
        - nodes: List[ { uuid, type, name?, values:{pid:value}, id? } ]
        - conns: List[ { uuid?, src_node, src_prop, dst_node, dst_prop } ]
        - positions: { uuid: [x, y] }
        - sizes: { uuid: [w, h] }
        """
        nodes_norm: List[dict] = []
        conns_norm: List[dict] = []
        positions: Dict[str, Tuple[float, float]] = {}
        sizes: Dict[str, Tuple[float, float]] = {}

        # Positions / sizes blocks used by our save_layout
        pos_block = data.get("positions", {}) or {}
        siz_block = data.get("sizes", {}) or {}
        if isinstance(pos_block, dict):
            positions = pos_block
        if isinstance(siz_block, dict):
            sizes = siz_block

        # Nodes block: accept dict keyed by uuid or list of node dicts.
        nodes_block = data.get("nodes")
        if isinstance(nodes_block, dict):
            for uuid_key, nd in nodes_block.items():
                norm = self._normalize_node_dict(uuid_key, nd)
                if norm:
                    # allow node-level position/size override if embedded
                    if isinstance(nd, dict):
                        if "pos" in nd and isinstance(nd["pos"], (list, tuple)) and len(nd["pos"]) == 2:
                            positions[norm["uuid"]] = nd["pos"]
                        if "size" in nd and isinstance(nd["size"], (list, tuple)) and len(nd["size"]) == 2:
                            sizes[norm["uuid"]] = nd["size"]
                    nodes_norm.append(norm)
        elif isinstance(nodes_block, list):
            for nd in nodes_block:
                uuid_key = None
                if isinstance(nd, dict):
                    uuid_key = nd.get("uuid") or nd.get("id")
                norm = self._normalize_node_dict(uuid_key, nd)
                if norm:
                    if isinstance(nd, dict):
                        if "pos" in nd and isinstance(nd["pos"], (list, tuple)) and len(nd["pos"]) == 2:
                            positions[norm["uuid"]] = nd["pos"]
                        if "size" in nd and isinstance(nd["size"], (list, tuple)) and len(nd["size"]) == 2:
                            sizes[norm["uuid"]] = nd["size"]
                    nodes_norm.append(norm)
        else:
            # Fallback: try graph-like root with 'graph' or 'items'
            for alt_key in ("graph", "items"):
                blk = data.get(alt_key)
                if isinstance(blk, list):
                    for nd in blk:
                        uuid_key = nd.get("uuid") if isinstance(nd, dict) else None
                        norm = self._normalize_node_dict(uuid_key, nd)
                        if norm:
                            nodes_norm.append(norm)
                elif isinstance(blk, dict):
                    for uuid_key, nd in blk.items():
                        norm = self._normalize_node_dict(uuid_key, nd)
                        if norm:
                            nodes_norm.append(norm)

        # Connections block: accept dict keyed by uuid or list.
        conns_block = data.get("connections") or data.get("edges") or data.get("links") or {}
        if isinstance(conns_block, dict):
            for cuuid, cd in conns_block.items():
                norm = self._normalize_conn_dict(cuuid, cd)
                if norm:
                    conns_norm.append(norm)
        elif isinstance(conns_block, list):
            for cd in conns_block:
                cuuid = cd.get("uuid") if isinstance(cd, dict) else None
                norm = self._normalize_conn_dict(cuuid, cd)
                if norm:
                    conns_norm.append(norm)

        return nodes_norm, conns_norm, positions, sizes

    def _normalize_node_dict(self, uuid_key: Optional[str], nd: Any) -> Optional[dict]:
        """Normalize a node dict to {uuid, type, name?, values{}, id?}."""
        if not isinstance(nd, dict):
            return None
        # Prefer explicit 'uuid' or the key from dict form; 'id' may be used for friendly label
        nuuid = nd.get("uuid") or uuid_key or nd.get("id")
        tname = nd.get("type") or nd.get("type_name") or nd.get("t")
        if not nuuid or not tname:
            return None
        name = nd.get("name") or nd.get("title") or nd.get("label")
        values = self._extract_values_from_properties_block(nd)

        # Extract friendly id if present and distinct from uuid to preserve per-layout numbering.
        friendly_id: Optional[str] = None
        try:
            raw_id = nd.get("id")
            if isinstance(raw_id, str):
                if (nd.get("uuid") and raw_id != nd.get("uuid")) or (uuid_key and raw_id != uuid_key) or (not nd.get("uuid") and not uuid_key):
                    friendly_id = raw_id
        except Exception:
            friendly_id = None

        res = {"uuid": nuuid, "type": tname, "name": name, "values": values}
        if friendly_id:
            res["id"] = friendly_id
        return res

    def _extract_values_from_properties_block(self, nd: dict) -> Dict[str, Any]:
        """Extract {prop_id: value} from various shapes of 'properties'."""
        values: Dict[str, Any] = {}
        block = nd.get("properties") or nd.get("props") or nd.get("fields") or {}
        if isinstance(block, dict):
            for k, v in block.items():
                if isinstance(v, dict):
                    if "value" in v:
                        values[k] = v.get("value")
                    elif "val" in v:
                        values[k] = v.get("val")
                    else:
                        # heuristics: take raw if simple type
                        values[k] = v.get("default") if "default" in v else v.get("data") if "data" in v else None
                else:
                    values[k] = v
        elif isinstance(block, list):
            for item in block:
                if not isinstance(item, dict):
                    continue
                pid = item.get("id") or item.get("key") or item.get("name")
                if not pid:
                    continue
                if "value" in item:
                    values[pid] = item.get("value")
                elif "val" in item:
                    values[pid] = item.get("val")
                elif "default" in item:
                    values[pid] = item.get("default")
        return values

    def _normalize_conn_dict(self, cuuid: Optional[str], cd: Any) -> Optional[dict]:
        """Normalize a connection dict to {uuid?, src_node, src_prop, dst_node, dst_prop}."""
        if not isinstance(cd, dict):
            return None
        s_n = cd.get("src_node") or cd.get("source") or cd.get("from_node")
        d_n = cd.get("dst_node") or cd.get("target") or cd.get("to_node")
        s_p = cd.get("src_prop") or cd.get("src") or cd.get("from") or cd.get("out")
        d_p = cd.get("dst_prop") or cd.get("dst") or cd.get("to") or cd.get("in")
        if not (s_n and d_n and s_p and d_p):
            # Try nested shapes: {src:{node,prop}, dst:{node,prop}}
            src = cd.get("src") or cd.get("from")
            dst = cd.get("dst") or cd.get("to")
            if isinstance(src, dict) and isinstance(dst, dict):
                s_n = src.get("node") or src.get("uuid")
                s_p = src.get("prop") or src.get("port") or src.get("id")
                d_n = dst.get("node") or dst.get("uuid")
                d_p = dst.get("prop") or dst.get("port") or dst.get("id")
        if not (s_n and d_n and s_p and d_p):
            return None
        return {"uuid": cuuid, "src_node": s_n, "src_prop": s_p, "dst_node": d_n, "dst_prop": d_p}

    # ---------- Compact layout serialization (value-only) ----------

    def _registry_prop_spec(self, type_name: str, prop_id: str) -> Optional[Any]:
        """Return the PropertySpec from the registry for given type/prop id, if available."""
        try:
            spec = self.graph.registry.get(type_name) if self.graph and self.graph.registry else None
            if not spec:
                return None
            props = getattr(spec, "properties", None)
            if isinstance(props, list):
                for ps in props:
                    if getattr(ps, "id", None) == prop_id:
                        return ps
            # Accept dict-like collections if registry exposes them
            for attr in ("props", "fields", "ports", "inputs", "outputs"):
                cont = getattr(spec, attr, None)
                if isinstance(cont, dict) and prop_id in cont:
                    return cont[prop_id]
        except Exception:
            return None
        return None

    def _should_persist_property(self, node: NodeModel, pm: PropertyModel) -> bool:
        """Decide whether a property should be written to layout.

        Rules:
            - Always include explicit base-id like fields (e.g. 'base_id') as they carry per-node state.
            - Include editable fields (typical user data).
            - Include non-editable fields only if their current value differs from registry default.
            - Ports (e.g., 'flow', 'memory') are skipped unless they carry a non-default value.
        """
        try:
            pid = pm.id
            if self._is_base_id_pid(pid, pm):
                return True

            # Editable properties are considered dynamic by nature
            if bool(getattr(pm, "editable", False)):
                return True

            # Compare with registry default to detect runtime changes
            ps = self._registry_prop_spec(node.type, pid)
            default = getattr(ps, "value", None) if ps is not None else None
            if pm.value != default:
                return True

            # Ports rarely carry a data value; skip when value equals default (usually None)
            return False
        except Exception:
            # Be conservative on errors: do not persist
            return False

    def _serialize_layout_compact(self) -> dict:
        """Build compact layout with minimal per-property data.

        Output shape:
            {
              "nodes": {
                "<node_uuid>": {
                  "uuid": "...",
                  "id": "...",
                  "name": "...",
                  "type": "Flow/Agent",
                  "properties": {
                    "<prop_id>": {
                      "uuid": "...",
                      "id": "name",
                      "name": "Name",
                      "value": "Alice",
                      "options": [...]    # only if options differ from registry default
                    },
                    ...
                  }
                },
                ...
              },
              "connections": {
                "<conn_uuid>": { "uuid": "...", "src_node": "...", "src_prop": "...", "dst_node": "...", "dst_prop": "..." },
                ...
              }
            }
        """
        nodes_out: Dict[str, dict] = {}
        for nuuid, n in self.graph.nodes.items():
            props_out: Dict[str, dict] = {}
            for pid, pm in n.properties.items():
                if not isinstance(pm, PropertyModel):
                    continue
                if not self._should_persist_property(n, pm):
                    continue

                entry = {
                    "uuid": pm.uuid,
                    "id": pm.id,
                    "name": pm.name,
                    "value": pm.value,
                }

                # Persist options only when they differ from registry default (dynamic options).
                try:
                    cur_opts = list(getattr(pm, "options", [])) if getattr(pm, "options", None) is not None else None
                    ps = self._registry_prop_spec(n.type, pid)
                    def_opts = list(getattr(ps, "options", [])) if ps is not None and getattr(ps, "options", None) is not None else None
                    if cur_opts is not None:
                        if def_opts is None or cur_opts != def_opts:
                            entry["options"] = cur_opts
                except Exception:
                    pass

                props_out[pid] = entry

            nodes_out[nuuid] = {
                "uuid": n.uuid,
                "id": n.id,
                "name": n.name,
                "type": n.type,
                "properties": props_out,
            }

        # Minimal connections (dict keyed by uuid for backwards compatibility)
        conns_out: Dict[str, dict] = {}
        for cuuid, c in self.graph.connections.items():
            conns_out[cuuid] = {
                "uuid": c.uuid,
                "src_node": c.src_node,
                "src_prop": c.src_prop,
                "dst_node": c.dst_node,
                "dst_prop": c.dst_prop,
            }

        return {"nodes": nodes_out, "connections": conns_out}

    # ---------- Overlay controls handlers ----------

    def _on_grab_toggled(self, enabled: bool):
        """Enable/disable global grab mode (left-button panning anywhere)."""
        if _qt_is_valid(self.view):
            self.view.set_global_grab_mode(bool(enabled))
        # Visual feedback is provided by the checkable state (style handles appearance)

    # ---------- Status label ----------

    def _update_status_label(self):
        """Compute node counts by type and update bottom-left status label."""
        try:
            counts: Dict[str, int] = {}
            unknown = self.config.type_unknown()
            for n in self.graph.nodes.values():
                t = getattr(n, "type", unknown) or unknown
                counts[t] = counts.get(t, 0) + 1
            if not counts:
                text = self.config.status_no_nodes()
            else:
                parts = [f"{k}: {counts[k]}" for k in sorted(counts.keys(), key=lambda s: s.lower())]
                text = ", ".join(parts)
            self._status.set_text(text)
            self._position_status_label()
        except Exception:
            pass