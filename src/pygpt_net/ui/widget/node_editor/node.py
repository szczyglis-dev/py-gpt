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
import re
from typing import Dict, Optional, List, Any, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, Signal, QEvent
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QWidget, QApplication, QGraphicsItem, QGraphicsWidget, QGraphicsProxyWidget, QStyleOptionGraphicsItem,
    QMenu, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLabel, QTextEdit, QPlainTextEdit
)

from pygpt_net.core.node_editor.graph import NodeGraph
from pygpt_net.core.node_editor.models import NodeModel, PropertyModel

from .command import MoveNodeCommand, ResizeNodeCommand
from .item import EdgeItem, PortItem, NodeOverlayItem
from .utils import _qt_is_valid

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QFontMetrics, QKeyEvent, QGuiApplication
from PySide6.QtWidgets import QTextEdit, QFrame

class SingleLineTextEdit(QTextEdit):
    editingFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lineEditLike")
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self.setFrameStyle(QFrame.NoFrame)
        self.document().setDocumentMargin(2)
        self._update_height()

    def _update_height(self):
        fm = QFontMetrics(self.font())
        h = fm.lineSpacing() + 8
        self.setFixedHeight(h)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (QEvent.FontChange, QEvent.ApplicationFontChange):
            self._update_height()

    def keyPressEvent(self, e: QKeyEvent):
        k = e.key()
        if k in (Qt.Key_Return, Qt.Key_Enter):
            self.clearFocus()
            self.editingFinished.emit()
            e.accept()
            return
        if k == Qt.Key_Backtab:
            self.focusPreviousChild()
            e.accept()
            return
        super().keyPressEvent(e)
        self._strip_newlines()

    def insertFromMimeData(self, source):
        text = source.text().replace("\r", " ").replace("\n", " ")
        self.insertPlainText(text)

    def _strip_newlines(self):
        t = self.toPlainText()
        t2 = t.replace("\r", " ").replace("\n", " ")
        if t != t2:
            pos = self.textCursor().position()
            self.blockSignals(True)
            self.setPlainText(t2)
            self.blockSignals(False)
            c = self.textCursor()
            c.setPosition(min(pos, len(t2)))
            self.setTextCursor(c)

    def _apply_menu_theme(self, menu: QMenu):
        """Apply app/window stylesheet + palette + font to context menu."""
        try:
            wnd = self.window()
        except Exception:
            wnd = None
        stylesheet = ""
        pal = None
        font = None
        try:
            if wnd:
                stylesheet = wnd.styleSheet() or ""
                pal = wnd.palette()
                font = wnd.font()
        except Exception:
            pass
        try:
            app = QApplication.instance()
            if app:
                if not stylesheet and app.styleSheet():
                    stylesheet = app.styleSheet()
                if pal is None:
                    pal = app.palette()
                if font is None:
                    font = app.font()
        except Exception:
            pass
        try:
            if pal:
                menu.setPalette(pal)
            if font:
                menu.setFont(font)
            if stylesheet:
                menu.setStyleSheet(stylesheet)
            menu.ensurePolished()
        except Exception:
            pass

    def contextMenuEvent(self, e):
        """Ensure standard context menu follows app-wide (e.g., Qt Material) styling."""
        try:
            menu = self.createStandardContextMenu()
        except Exception:
            return super().contextMenuEvent(e)
        self._apply_menu_theme(menu)
        try:
            menu.exec(e.globalPos())
        finally:
            try:
                menu.deleteLater()
            except Exception:
                pass


class NodeContentWidget(QWidget):
    """Form-like widget that renders property editors for a node.

    The widget builds appropriate Qt editors based on PropertyModel.type:
        - "str": QLineEdit
        - "text": QTextEdit
        - "int": QSpinBox
        - "float": QDoubleSpinBox
        - "bool": QCheckBox
        - "combo": QComboBox
        - other: QLabel (disabled)

    It emits valueChanged(prop_id, value) when a field is edited.

    Notes:
        - For Base ID-like properties, the field is read-only; a composed display value is shown.
        - ShortcutOverride is handled so typing in editors does not trigger scene shortcuts.

    Signal:
        valueChanged(str, object): Emitted when the value of a property changes.
    """
    valueChanged = Signal(str, object)

    def __init__(self, node: NodeModel, graph: NodeGraph, editor: "NodeEditor", parent: Optional[QWidget] = None):
        """Build all property editors from the node model/specification."""
        super().__init__(parent)
        self.node = node
        self.graph = graph
        self.editor = editor
        self.setObjectName("NodeContentWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.form = QFormLayout(self)
        self.form.setContentsMargins(8, 8, 8, 8)
        self.form.setSpacing(6)
        self._editors: Dict[str, QWidget] = {}
        for pid, pm in node.properties.items():
            editable = self._editable_from_spec(pid, pm)
            w: QWidget
            if pm.type == "str":
                te = SingleLineTextEdit()
                te.setFocusPolicy(Qt.StrongFocus)

                txt = ""
                if pm.value is not None:
                    try:
                        txt = str(pm.value)
                    except Exception:
                        txt = f"{pm.value}"

                if self._is_base_id_property(pid, pm):
                    txt = self._compose_base_id_display(pid, txt)
                    te.setReadOnly(True)
                    te.setFocusPolicy(Qt.NoFocus)
                else:
                    te.setReadOnly(not editable)

                te.setPlainText(txt)
                te.textChanged.connect(lambda pid=pid, te=te: self.valueChanged.emit(pid, te.toPlainText()))
                te.editingFinished.connect(lambda pid=pid, te=te: self.valueChanged.emit(pid, te.toPlainText()))
                w = te
            elif pm.type == "text":
                te = QTextEdit()
                te.setFocusPolicy(Qt.StrongFocus)
                if pm.value is not None:
                    te.setPlainText(str(pm.value))
                te.setReadOnly(not editable)
                te.textChanged.connect(lambda pid=pid, te=te: self.valueChanged.emit(pid, te.toPlainText()))
                # Ensure context menu follows global (Material) style
                self._install_styled_context_menu(te)
                w = te
            elif pm.type == "int":
                w = QSpinBox()
                w.setFocusPolicy(Qt.StrongFocus)
                w.setRange(-10**9, 10**9)
                if pm.value is not None:
                    w.setValue(int(pm.value))
                w.setEnabled(editable)
                w.valueChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, int(v)))
            elif pm.type == "float":
                w = QDoubleSpinBox()
                w.setFocusPolicy(Qt.StrongFocus)
                w.setDecimals(4)
                w.setRange(-1e12, 1e12)
                if pm.value is not None:
                    w.setValue(float(pm.value))
                w.setEnabled(editable)
                w.valueChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, float(v)))
            elif pm.type == "bool":
                w = QCheckBox()
                w.setFocusPolicy(Qt.StrongFocus)
                if pm.value:
                    w.setChecked(bool(pm.value))
                w.setEnabled(editable)
                w.toggled.connect(lambda v, pid=pid: self.valueChanged.emit(pid, bool(v)))
            elif pm.type == "combo":
                w = QComboBox()
                w.setFocusPolicy(Qt.StrongFocus)
                for opt in (pm.options or []):
                    w.addItem(opt)
                if pm.value is not None and pm.value in (pm.options or []):
                    w.setCurrentText(pm.value)
                w.setEnabled(editable)
                w.currentTextChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, v))
            else:
                # Render a read-only capacity placeholder for port-like properties ("input/output").
                cap_text = self._capacity_text_for_property(pid, pm)
                w = QLabel(cap_text)
                w.setEnabled(False)
                w.setToolTip(self.editor.config.port_capacity_tooltip(cap_text))

            name = self._display_name_for_property(pid, pm)
            if name == "Base ID":
                name = self.editor.config.label_id()
            self.form.addRow(name, w)
            self._editors[pid] = w

    def _install_styled_context_menu(self, te: QTextEdit):
        """Install a custom context menu handler that applies global styles."""
        try:
            te.setContextMenuPolicy(Qt.CustomContextMenu)
            te.customContextMenuRequested.connect(
                lambda pos, _te=te: self._show_styled_standard_menu(_te, pos)
            )
        except Exception:
            pass

    def _show_styled_standard_menu(self, te: QTextEdit, pos):
        """Create standard menu and apply app/window stylesheet + palette + font."""
        try:
            menu = te.createStandardContextMenu()
        except Exception:
            return
        stylesheet = ""
        pal = None
        font = None
        try:
            # Prefer editor helpers (consistent with the rest of NodeEditor)
            stylesheet = self.editor._current_stylesheet()
            pal = self.editor._current_palette()
            font = self.editor._current_font()
        except Exception:
            try:
                wnd = te.window()
                if wnd:
                    stylesheet = wnd.styleSheet() or ""
                    pal = wnd.palette()
                    font = wnd.font()
            except Exception:
                pass
        try:
            if pal:
                menu.setPalette(pal)
            if font:
                menu.setFont(font)
            if stylesheet:
                menu.setStyleSheet(stylesheet)
            menu.ensurePolished()
        except Exception:
            pass
        try:
            menu.exec(te.mapToGlobal(pos))
        finally:
            try:
                menu.deleteLater()
            except Exception:
                pass

    def event(self, e):
        """
        Filter ShortcutOverride so editor keystrokes are not eaten by the scene.

        Allows space, backspace and delete to be used inside text-like editors.
        """
        if e.type() == QEvent.ShortcutOverride:
            key = getattr(e, "key", lambda: None)()
            if key in (Qt.Key_Space, Qt.Key_Backspace, Qt.Key_Delete):
                fw = QApplication.focusWidget()
                if fw and (fw is self or self.isAncestorOf(fw)):
                    try:
                        if isinstance(fw, (QLineEdit, QTextEdit, QPlainTextEdit)):
                            if not (hasattr(fw, "isReadOnly") and fw.isReadOnly()):
                                e.accept()
                                return True
                        if isinstance(fw, QComboBox) and fw.isEditable():
                            e.accept()
                            return True
                        if isinstance(fw, (QSpinBox, QDoubleSpinBox)) and fw.hasFocus():
                            e.accept()
                            return True
                    except Exception:
                        pass
        return super().event(e)

    def _display_name_for_property(self, pid: str, pm: PropertyModel) -> str:
        """Resolve a human-friendly label for a property from the registry or fallback to model.

        Strategy:
            1) Try different attribute containers in the type spec (properties, props, fields, ports, inputs, outputs)
               looking for name/label/title.
            2) Try getter-like methods on the type spec (get_property, property_spec, get_prop, prop, property).
            3) Fallback to PropertyModel.name, then to the pid.

        Returns:
            Display name string.

        Example:
            If registry spec has:
                spec.properties["text_input"] = {"name": "Text", "editable": True}
            then the display name is "Text".
        """
        try:
            spec = self.graph.registry.get(self.node.type)
            if spec is not None:
                def _extract_name(obj) -> Optional[str]:
                    if obj is None:
                        return None
                    for key in ("name", "label", "title"):
                        try:
                            val = getattr(obj, key, None)
                            if val:
                                return str(val)
                        except Exception:
                            pass
                        try:
                            if isinstance(obj, dict) and obj.get(key):
                                return str(obj[key])
                        except Exception:
                            pass
                    return None
                for attr in ("properties", "props", "fields", "ports", "inputs", "outputs"):
                    try:
                        cont = getattr(spec, attr, None)
                        if isinstance(cont, dict) and pid in cont:
                            n = _extract_name(cont[pid])
                            if n:
                                return n
                    except Exception:
                        pass
                for meth in ("get_property", "property_spec", "get_prop", "prop", "property"):
                    if hasattr(spec, meth):
                        try:
                            n = _extract_name(getattr(spec, meth)(pid))
                            if n:
                                return n
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            if getattr(pm, "name", None):
                return str(pm.name)
        except Exception:
            pass
        return pid

    def _editable_from_spec(self, pid: str, pm: PropertyModel) -> bool:
        """Return whether the given property is editable, based on spec or model default.

        Resolution order:
            - spec.properties[pid].editable (or alias keys)
            - getattr(spec, method)(pid).editable
            - PropertyModel.editable (default True)

        Returns:
            bool: True when editable.

        Caveat:
            This is UI-only; the graph validation rules still apply when saving/applying values.
        """
        try:
            spec = self.graph.registry.get(self.node.type)
            if spec is not None:
                for attr in ("properties", "props", "fields"):
                    try:
                        cont = getattr(spec, attr, None)
                        if isinstance(cont, dict) and pid in cont:
                            obj = cont[pid]
                            val = None
                            try:
                                val = getattr(obj, "editable", None)
                            except Exception:
                                pass
                            if val is None and isinstance(obj, dict):
                                val = obj.get("editable")
                            if isinstance(val, bool):
                                return val
                    except Exception:
                        pass
                for meth in ("get_property", "property_spec", "get_prop", "prop", "property"):
                    if hasattr(spec, meth):
                        try:
                            obj = getattr(spec, meth)(pid)
                            val = None
                            try:
                                val = getattr(obj, "editable", None)
                            except Exception:
                                pass
                            if val is None and isinstance(obj, dict):
                                val = obj.get("editable")
                            if isinstance(val, bool):
                                return val
                        except Exception:
                            pass
        except Exception:
            pass
        return bool(getattr(pm, "editable", True))

    def _capacity_text_for_property(self, pid: str, pm: PropertyModel) -> str:
        """Return 'IN/OUT' capacity text using live spec (fallback to PropertyModel)."""
        try:
            # NodeEditor helper returns (out_allowed, in_allowed)
            out_allowed, in_allowed = self.editor._allowed_from_spec(self.node, pid)
        except Exception:
            # Fallback to model fields when spec is unavailable
            try:
                out_allowed = int(getattr(pm, "allowed_outputs", 0) or 0)
            except Exception:
                out_allowed = 0
            try:
                in_allowed = int(getattr(pm, "allowed_inputs", 0) or 0)
            except Exception:
                in_allowed = 0

        def fmt(v: object) -> str:
            try:
                iv = int(v)
            except Exception:
                return "-"
            if iv < 0:
                return "\u221E"
            if iv == 0:
                return "-"
            return str(iv)

        # Display order: INPUT/OUTPUT
        return f"{fmt(in_allowed)}/{fmt(out_allowed)}"

    # --- Base ID helpers (UI-only) ---

    def _is_base_id_property(self, pid: str, pm: PropertyModel) -> bool:
        """Heuristically detect 'Base ID'-like properties by flags, pid or name."""
        try:
            if getattr(pm, "is_base_id", False):
                return True
        except Exception:
            pass
        name_key = (pm.name or "").strip().lower().replace(" ", "_") if hasattr(pm, "name") else ""
        pid_key = (pid or "").strip().lower().replace(" ", "_")
        candidates = {"base_id", "baseid", "base", "id_base", "basename", "base_name"}
        return pid_key in candidates or name_key in candidates

    def _compose_base_id_display(self, pid: str, base_value: str) -> str:
        """Compose a read-only display for 'Base ID' editor.

        If the base value already ends with _<digits> then it is returned unchanged.
        Otherwise, try to find an existing suffix from other properties/attrs and append it.

        Returns:
            str: Display value with a reusable or inferred suffix if applicable.

        Example:
            base_value='agent' and node.meta['index']=3 -> 'agent_3'
        """
        if not isinstance(base_value, str):
            base_value = f"{base_value}"
        if re.match(r".+_\d+$", base_value):
            return base_value
        suffix = self._resolve_existing_suffix(pid, base_value)
        if suffix is None:
            return base_value
        try:
            s = int(str(suffix))
            return f"{base_value}_{s}"
        except Exception:
            s = f"{suffix}".strip()
            if not s:
                return base_value
            s = s.lstrip("_")
            return f"{base_value}_{s}"

    def _resolve_existing_suffix(self, pid: str, base_value: str) -> Optional[Any]:
        """Try to reuse a numeric or string suffix from the node/graph context.

        Checks in order:
            - Sibling properties: id_suffix, suffix, index, seq, order, counter, num
            - Node attributes: idIndex, human_index, friendly_index
            - Dict-like containers: meta, data, extras, extra, ctx
            - Graph-level similarity: for nodes with the same base value, uses a stable
              enumeration order to compute an index (1-based).

        Args:
            pid: Property id considered a 'base' key.
            base_value: Base string without suffix.

        Returns:
            Optional[Any]: The found suffix, or None if nothing suitable is detected.
        """
        prop_keys = ("id_suffix", "suffix", "index", "seq", "order", "counter", "num")
        for key in prop_keys:
            try:
                pm = self.node.properties.get(key)
                if pm is not None and pm.value not in (None, ""):
                    return pm.value

            except Exception:
                pass

        attr_keys = prop_keys + ("idIndex", "human_index", "friendly_index")
        for key in attr_keys:
            try:
                if hasattr(self.node, key):
                    val = getattr(self.node, key)
                    if val not in (None, ""):
                        return val
            except Exception:
                pass
        for dict_name in ("meta", "data", "extras", "extra", "ctx"):
            try:
                d = getattr(self.node, dict_name, None)
                if isinstance(d, dict):
                    for k in prop_keys:
                        if k in d and d[k] not in (None, ""):
                            return d[k]
            except Exception:
                pass

        try:
            if self.graph and hasattr(self.graph, "nodes") and isinstance(self.graph.nodes, dict):
                def _base_of(n: NodeModel) -> Optional[str]:
                    try:
                        ppm = n.properties.get(pid)
                        return None if ppm is None or ppm.value is None else str(ppm.value)
                    except Exception:
                        return None
                same = [n for n in self.graph.nodes.values() if _base_of(n) == base_value]
                if not same:
                    return None
                same_sorted = sorted(same, key=lambda n: getattr(n, "uuid", ""))
                idx = next((i for i, n in enumerate(same_sorted) if getattr(n, "uuid", None) == getattr(self.node, "uuid", None)), None)
                if idx is not None:
                    return idx + 1
        except Exception:
            pass

        return None


class NodeItem(QGraphicsWidget):
    """Rounded node with title and ports aligned to property rows.

    The node embeds a QWidget (NodeContentWidget) via QGraphicsProxyWidget to render
    property editors. Input/output ports are aligned with editor rows for easy wiring.
    """

    def __init__(self, editor: "NodeEditor", node: NodeModel):
        """Construct a node item and build its child content/ports.

        Args:
            editor: Owning NodeEditor instance.
            node: Backing NodeModel with properties and type.
        """
        super().__init__()
        self.editor = editor
        self.graph = editor.graph
        self.node = node
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(2)
        self._title_height = 24
        self._radius = 6
        self._proxy = QGraphicsProxyWidget(self)
        self._content = NodeContentWidget(node, self.graph, self.editor)
        self._content.setMouseTracking(True)
        self._content.setAttribute(Qt.WA_Hover, True)
        self._proxy.setWidget(self._content)
        self._proxy.setAcceptHoverEvents(True)
        self._proxy.installEventFilter(self)
        self._proxy.setPos(0, self._title_height)
        self._content.installEventFilter(self)
        self._content.valueChanged.connect(self._on_value_changed)
        self._in_ports: Dict[str, PortItem] = {}
        self._out_ports: Dict[str, PortItem] = {}
        self._edges: List[EdgeItem] = []
        self._prev_pos = self.pos()

        self._dragging = False
        self._overlaps = False
        self._start_pos = QPointF(self.pos())
        self._last_valid_pos = QPointF(self.pos())
        self._z_before_drag = self.zValue()

        self.setAcceptHoverEvents(True)
        self.setFiltersChildEvents(True)
        self._resizing: bool = False
        self._resize_mode: str = "none"
        self._resize_press_local = QPointF()
        self._resize_start_size = QSizeF()
        self._hover_resize_mode: str = "none"

        self._overlay = NodeOverlayItem(self)

        # Enable scene-dependent logic only when safely added to the scene
        self._ready_scene_ops: bool = False

        self._sync_size()
        self._build_ports()
        self._sync_size()

    # ---------- Spec helpers ----------
    def _get_prop_spec(self, pid: str) -> Optional[Any]:
        """Return a property specification object from the registry for this node type.

        Searches common containers and getter methods to be resilient to spec shapes.
        """
        try:
            reg = self.graph.registry
            if not reg:
                return None
            type_spec = reg.get(self.node.type)
            if not type_spec:
                return None

            for attr in ("properties", "props", "fields", "ports", "inputs", "outputs"):
                try:
                    cont = getattr(type_spec, attr, None)
                    if isinstance(cont, dict) and pid in cont:
                        return cont[pid]
                except Exception:
                    pass
            for meth in ("get_property", "property_spec", "get_prop", "prop", "property"):
                if hasattr(type_spec, meth):
                    try:
                        return getattr(type_spec, meth)(pid)
                    except Exception:
                        pass
        except Exception:
            pass
        return None

    def _spec_int(self, obj: Any, key: str, default: Optional[int]) -> Optional[int]:
        """Get an integer attribute/key from a spec object or dict, with default."""
        if obj is None:
            return default
        try:
            v = getattr(obj, key, None)
            if isinstance(v, int):
                return v
        except Exception:
            pass
        try:
            if isinstance(obj, dict):
                v = obj.get(key)
                if isinstance(v, int):
                    return v
        except Exception:
            pass
        return default

    def allowed_capacity_for_pid(self, pid: str, side: str) -> Optional[int]:
        """Return allowed connection capacity for a given property id and side ('input'/'output')."""
        spec = self._get_prop_spec(pid)
        if side == "input":
            return self._spec_int(spec, "allowed_inputs", self._pm_allowed(pid, inputs=True))
        else:
            return self._spec_int(spec, "allowed_outputs", self._pm_allowed(pid, inputs=False))

    def _pm_allowed(self, pid: str, inputs: bool) -> Optional[int]:
        """Fallback to the PropertyModel's allowed_inputs/allowed_outputs if spec is absent."""
        pm = self.node.properties.get(pid)
        if not pm:
            return None
        return int(getattr(pm, "allowed_inputs" if inputs else "allowed_outputs", 0))

    # ---------- Size helpers ----------
    def _effective_hit_margin(self) -> float:
        """Return the effective resize-grip 'hit' margin (visual margin minus inset)."""
        margin = float(getattr(self.editor, "_resize_grip_margin", 12.0) or 12.0)
        inset = float(getattr(self.editor, "_resize_grip_hit_inset", 3.0) or 0.0)
        hit = max(4.0, margin - inset)
        return hit

    def _min_size_from_content(self) -> QSizeF:
        """Compute the minimal node size based on content size plus paddings and grips."""
        csz = self._content.sizeHint() if _qt_is_valid(self._content) else QSizeF(120, 40)
        hit = self._effective_hit_margin()
        w = max(80.0, float(csz.width()) + 16.0 + hit)
        h_auto = float(csz.height()) + 16.0 + float(self._title_height) + hit
        h = max(float(self._title_height + 16 + hit), h_auto)
        return QSizeF(w, h)

    def _apply_resize(self, new_size: QSizeF, clamp: bool = True):
        """Resize the node and child proxy, optionally clamping to min size.

        Args:
            new_size: Requested QSizeF.
            clamp: If True, clamp to the minimal size computed from content.

        Side effects:
            - Resizes QGraphicsWidget and its proxy widget.
            - Recomputes port positions and updates overlay.
        """
        hit = self._effective_hit_margin()
        minsz = self._min_size_from_content() if clamp else QSizeF(0.0, 0.0)
        w = max(minsz.width(), float(new_size.width()))
        h = max(minsz.height(), float(new_size.height()))
        if _qt_is_valid(self._overlay):
            try:
                self._overlay.prepareGeometryChange()
            except Exception:
                pass
        self.resize(QSizeF(w, h))
        ph = max(0.0, h - self._title_height - hit)
        pw = max(0.0, w - hit)
        if _qt_is_valid(self._proxy):
            try:
                self._proxy.resize(pw, ph)
                if _qt_is_valid(self._content) and self._content.layout():
                    try:
                        self._content.layout().activate()
                    except Exception:
                        pass
            except Exception:
                pass
        self.update_ports_positions()
        if _qt_is_valid(self._overlay):
            try:
                self._overlay.update()
            except Exception:
                pass
        self.update()

    def _sync_size(self):
        """Size the node to fit content with paddings and current hit margin."""
        csz = self._content.sizeHint()
        hit = self._effective_hit_margin()
        w = float(csz.width()) + 16.0 + hit
        auto_h = float(csz.height()) + 16.0 + float(self._title_height) + hit
        h = max(auto_h, float(self._title_height + 16 + hit))
        if _qt_is_valid(self._overlay):
            try:
                self._overlay.prepareGeometryChange()
            except Exception:
                pass
        self.resize(QSizeF(w, h))
        self._proxy.resize(max(0.0, w - hit), max(0.0, h - self._title_height - hit))

    # ---------- Port alignment ----------

    def _compute_port_y_for_pid(self, pid: str) -> float:
        """Compute the Y position for the port corresponding to a property id.

        Aligns ports to editor rows; for multi-line editors (QTextEdit) uses top edge.
        """
        try:
            w = self._content._editors.get(pid)
            if w is not None and isinstance(w, QWidget):
                geo = w.geometry()
                base_y = float(self._proxy.pos().y()) + float(geo.y())
                if isinstance(w, QTextEdit):
                    return base_y
                return base_y + float(geo.height()) * 0.5
        except Exception:
            pass

        idx = 0
        try:
            keys = list(self.node.properties.keys())
            idx = keys.index(pid)
        except Exception:
            pass
        yoff = self._title_height + 8 + 24 * idx
        return float(yoff + 8)

    def _build_ports(self):
        """Create input/output PortItem(s) according to allowed capacities in the spec."""
        for pid, pm in self.node.properties.items():
            cap_in = self.allowed_capacity_for_pid(pid, "input")
            cap_out = self.allowed_capacity_for_pid(pid, "output")
            if isinstance(cap_in, int) and cap_in != 0:
                p = PortItem(self, pid, "input")
                p.setPos(-10, self._compute_port_y_for_pid(pid))
                p.portClicked.connect(self.editor._on_port_clicked)
                self._in_ports[pid] = p
            if isinstance(cap_out, int) and cap_out != 0:
                p = PortItem(self, pid, "output")
                p.setPos(self.size().width() + 10, self._compute_port_y_for_pid(pid))
                p.portClicked.connect(self.editor._on_port_clicked)
                self._out_ports[pid] = p
        self.update_ports_positions()

    def update_ports_positions(self):
        """Reposition ports along the left/right edges and refresh attached edges."""
        for pid in self.node.properties.keys():
            y = self._compute_port_y_for_pid(pid)
            if pid in self._in_ports:
                self._in_ports[pid].setPos(-10, y)
                self._in_ports[pid].update_labels()
            if pid in self._out_ports:
                self._out_ports[pid].setPos(self.size().width() + 10, y)
                self._out_ports[pid].update_labels()
        for e in self._edges:
            e.update_path()
        if _qt_is_valid(self._overlay):
            try:
                self._overlay.update()
            except Exception:
                pass

    def add_edge(self, edge: EdgeItem):
        """Track an edge that connects to this node."""
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge(self, edge: EdgeItem):
        """Stop tracking an edge (called before edge removal)."""
        if edge in self._edges:
            self._edges.remove(edge)

    def boundingRect(self) -> QRectF:
        """Return the node's local bounding rect."""
        return QRectF(0, 0, self.size().width(), self.size().height())

    def _hit_resize_zone(self, pos: QPointF) -> str:
        """Return which resize zone is hit: 'right', 'bottom', 'corner', or 'none'."""
        w = self.size().width()
        h = self.size().height()
        hit = self._effective_hit_margin()
        right = (w - hit) <= pos.x() <= w
        bottom = (h - hit) <= pos.y() <= h
        if right and bottom:
            return "corner"
        if right:
            return "right"
        if bottom:
            return "bottom"
        return "none"

    def _pid_from_content_y(self, y_local: float) -> Optional[str]:
        """Map a local Y (NodeItem coords) to property id of the hovered editor row."""
        try:
            proxy_off = self._proxy.pos()
            for pid, w in self._content._editors.items():
                if not _qt_is_valid(w):
                    continue
                geo = w.geometry()
                top = float(proxy_off.y()) + float(geo.y())
                bottom = top + float(geo.height())
                if top <= y_local <= bottom:
                    return pid
        except Exception:
            pass
        return None

    def paint(self, p: QPainter, opt: QStyleOptionGraphicsItem, widget=None):
        """Draw rounded background, title bar, border, resize hint, and node title."""
        r = self.boundingRect()
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        p.setRenderHint(QPainter.Antialiasing, True)

        bg = self.editor._node_bg_color
        try:
            spec = self.graph.registry.get(self.node.type)
            if spec and getattr(spec, "bg_color", None):
                c = QColor(spec.bg_color)
                if c.isValid():
                    bg = c
        except Exception:
            pass

        border = self.editor._node_border_color
        if self.isSelected():
            border = self.editor._node_selection_color
        p.fillPath(path, QBrush(bg))
        pen = QPen(border)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawPath(path)
        title_rect = QRectF(r.left(), r.top(), r.width(), self._title_height)
        p.fillRect(title_rect, self.editor._node_title_color)
        p.setPen(QPen(Qt.white))
        p.drawText(title_rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, self.node.name)

        hit = self._effective_hit_margin()
        mode = self._resize_mode if self._resizing else self._hover_resize_mode
        hl = QColor(border)
        hl.setAlpha(110)
        if mode in ("right", "corner"):
            p.fillRect(QRectF(r.right() - hit, r.top() + self._title_height, hit, r.height() - self._title_height), hl)
        if mode in ("bottom", "corner"):
            p.fillRect(QRectF(r.left(), r.bottom() - hit, r.width(), hit), hl)

        tri_color = border.lighter(150)
        tri_color.setAlpha(140)
        corner = QPainterPath()
        corner.moveTo(r.right() - hit + 1, r.bottom() - 1)
        corner.lineTo(r.right() - 1, r.bottom() - hit + 1)
        corner.lineTo(r.right() - 1, r.bottom() - 1)
        corner.closeSubpath()
        p.fillPath(corner, tri_color)

        hatch_pen = QPen(border.lighter(170), 1.6)
        hatch_pen.setCosmetic(True)
        p.setPen(hatch_pen)
        x1 = r.right() - 5
        y1 = r.bottom() - 1
        for i in range(3):
            p.drawLine(QPointF(x1 - 5 * i, y1), QPointF(r.right() - 1, r.bottom() - 5 - 5 * i))

    def _apply_hover_from_pos(self, pos: QPointF):
        """Update cursor and highlight for resize zones based on a local position.

        Also sets a 'move' cursor (SizeAll) when hovering over the draggable area
        of the node (title bar and non-interactive content gaps).
        """
        if self._resizing:
            return

        # When global grab mode is active, suppress resize/move cursors
        view = self.editor.view
        if getattr(view, "_global_grab_mode", False):
            self._hover_resize_mode = "none"
            self.unsetCursor()
            self.update()
            return

        mode = self._hit_resize_zone(pos)
        self._hover_resize_mode = mode

        # Resize cursors have priority
        if mode == "corner":
            self.setCursor(Qt.SizeFDiagCursor)
        elif mode == "right":
            self.setCursor(Qt.SizeHorCursor)
        elif mode == "bottom":
            self.setCursor(Qt.SizeVerCursor)
        else:
            # Show move cursor on the title bar or non-interactive content area
            show_move = False

            # Title bar (always draggable)
            if pos.y() <= self._title_height:
                show_move = True
            else:
                # Inside content: only if not hovering an interactive editor
                if _qt_is_valid(self._content) and _qt_is_valid(self._proxy):
                    local_in_content = pos - self._proxy.pos()
                    cx = int(local_in_content.x())
                    cy = int(local_in_content.y())
                    if 0 <= cx < int(self._content.width()) and 0 <= cy < int(self._content.height()):
                        hovered = self._content.childAt(cx, cy)
                        # Treat labels/empty gaps as draggable area (safe to move)
                        if hovered is None or isinstance(hovered, QLabel):
                            show_move = True

            if show_move:
                self.setCursor(Qt.SizeAllCursor)  # 4-way move cursor
            else:
                self.unsetCursor()

        self.update()

    def hoverMoveEvent(self, event):
        """While panning is active or global grab is enabled, suppress resize hints; otherwise update hover state."""
        view = self.editor.view
        if getattr(view, "_panning", False) or getattr(view, "_global_grab_mode", False):
            self._hover_resize_mode = "none"
            self.unsetCursor()
            self.update()
            return super().hoverMoveEvent(event)

        self._apply_hover_from_pos(event.pos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        """Reset hover-related visuals when cursor leaves the item."""
        if not self._resizing:
            self._hover_resize_mode = "none"
            self.unsetCursor()
            self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Start resize when pressing the proper zone; otherwise begin move drag."""
        # Always bring clicked node to front (dynamic z-order)
        try:
            self.editor.raise_node_to_top(self)
        except Exception:
            pass

        # If global grab is active, do not initiate node drag/resize (view handles panning)
        if getattr(self.editor.view, "_global_grab_mode", False) and event.button() == Qt.LeftButton:
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            mode = self._hit_resize_zone(event.pos())
            if mode != "none":
                self._resizing = True
                self._resize_mode = mode
                self._resize_press_local = QPointF(event.pos())
                self._resize_start_size = QSizeF(self.size())
                self._z_before_drag = self.zValue()
                self.setZValue(self._z_before_drag + 100)
                if mode == "corner":
                    self.setCursor(Qt.SizeFDiagCursor)
                elif mode == "right":
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.setCursor(Qt.SizeVerCursor)
                event.accept()
                return

            self._dragging = True
            self._overlaps = False
            self._start_pos = QPointF(self.pos())
            self._last_valid_pos = QPointF(self.pos())
            self._z_before_drag = self.zValue()
            self.setZValue(self._z_before_drag + 100)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Resize while in resize mode; otherwise update hover visual and defer to base."""
        if self._resizing:
            dx = float(event.pos().x() - self._resize_press_local.x())
            dy = float(event.pos().y() - self._resize_press_local.y())
            w = self._resize_start_size.width()
            h = self._resize_start_size.height()
            if self._resize_mode in ("right", "corner"):
                w = self._resize_start_size.width() + dx
            if self._resize_mode in ("bottom", "corner"):
                h = self._resize_start_size.height() + dy
            self._apply_resize(QSizeF(w, h), clamp=True)
            event.accept()
            return
        else:
            self._apply_hover_from_pos(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Finalize resize/move and push corresponding undo commands when needed."""
        if self._resizing and event.button() == Qt.LeftButton:
            self._resizing = False
            self.setZValue(self._z_before_drag)
            self._apply_hover_from_pos(event.pos())
            new_size = QSizeF(self.size())
            if abs(new_size.width() - self._resize_start_size.width()) > 0.5 or \
               abs(new_size.height() - self._resize_start_size.height()) > 0.5:
                self.editor._undo.push(ResizeNodeCommand(self, self._resize_start_size, new_size))
            self._resize_mode = "none"
            event.accept()
            return

        if self._dragging and event.button() == Qt.LeftButton:
            if bool(getattr(self.editor, "enable_collisions", True)) and self._overlaps:
                self.setPos(self._last_valid_pos)
            else:
                if self.pos() != self._start_pos:
                    self.editor._undo.push(MoveNodeCommand(self, self._start_pos, self.pos()))
            self.setOpacity(1.0)
            self.setZValue(self._z_before_drag)
            self._dragging = False
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, e):
        """Filter events on proxy/content to keep hover/ports/overlay in sync."""
        et = e.type()
        try:
            if obj is self._proxy and et in (QEvent.GraphicsSceneMouseMove, QEvent.GraphicsSceneHoverMove):
                local = self.mapFromScene(e.scenePos())
                self._apply_hover_from_pos(local)
                # Row hover is controlled from content events; proxy move only updates resize hints.
                return False

            if obj is self._proxy and et in (QEvent.GraphicsSceneResize,):
                self.update_ports_positions()
                if _qt_is_valid(self._overlay):
                    self._overlay.update()
                return False

            if obj is self._proxy and et == QEvent.GraphicsSceneHoverLeave:
                if not self._resizing:
                    self._hover_resize_mode = "none"
                    self.unsetCursor()
                    self.update()
                # Clear row hover when leaving proxy area
                if _qt_is_valid(self._overlay):
                    try:
                        self._overlay.set_hover_pid(None)
                    except Exception:
                        pass
                return False

            if obj is self._content and et in (QEvent.MouseMove, QEvent.HoverMove, QEvent.Enter):
                # Track pointer over content to drive row hover highlight
                if hasattr(e, "position"):
                    p = e.position()
                    px, py = float(p.x()), float(p.y())
                elif hasattr(e, "pos"):
                    p = e.pos()
                    px, py = float(p.x()), float(p.y())
                else:
                    px = py = 0.0
                base = self._proxy.pos()
                local = QPointF(base.x() + px, base.y() + py)

                self._apply_hover_from_pos(local)

                if _qt_is_valid(self._overlay):
                    try:
                        pid = self._pid_from_content_y(local.y())
                        self._overlay.set_hover_pid(pid)
                    except Exception:
                        pass
                return False

            if obj is self._content and et in (QEvent.Leave, QEvent.HoverLeave):
                # Clear row hover when leaving the content area
                if _qt_is_valid(self._overlay):
                    try:
                        self._overlay.set_hover_pid(None)
                    except Exception:
                        pass
                return False

            if obj is self._content and et in (QEvent.Resize, QEvent.LayoutRequest):
                self.update_ports_positions()
                if _qt_is_valid(self._overlay):
                    self._overlay.update()
                return False

            if obj is self._content and et == QEvent.MouseButtonPress:
                # Bring to front when clicking inside embedded editors (proxy widget area)
                try:
                    self.editor.raise_node_to_top(self)
                except Exception:
                    pass
                return False
        except Exception:
            pass
        return False

    def itemChange(self, change, value):
        """Handle collision hints during move and update edge paths after movement."""
        # Avoid touching the scene during construction/destruction/GC or while editor is closing
        if change == QGraphicsItem.ItemPositionChange:
            try:
                if not getattr(self, "_ready_scene_ops", False):
                    return value
                ed = getattr(self, "editor", None)
                if ed is None or not getattr(ed, "_alive", True) or getattr(ed, "_closing", False):
                    return value
                # Only evaluate overlaps while actively dragging (safe user interaction only)
                if not getattr(self, "_dragging", False):
                    return value

                # When collisions are disabled, skip overlap checks entirely
                if not bool(getattr(self.editor, "enable_collisions", True)):
                    self._overlaps = False
                    return value

                sc = self.scene()
                if sc is None or not _qt_is_valid(sc):
                    return value

                new_pos: QPointF = value
                new_rect = QRectF(new_pos.x(), new_pos.y(), self.size().width(), self.size().height())
                overlap = False
                for it in sc.items(new_rect, Qt.IntersectsItemBoundingRect):
                    if it is self:
                        continue
                    if isinstance(it, NodeItem):
                        other = QRectF(it.scenePos().x(), it.scenePos().y(), it.size().width(), it.size().height())
                        if new_rect.adjusted(1, 1, -1, -1).intersects(other.adjusted(1, 1, -1, -1)):
                            overlap = True
                            break
                self._overlaps = overlap
                try:
                    self.setOpacity(0.5 if overlap else 1.0)
                except Exception:
                    pass
                if not overlap:
                    self._last_valid_pos = new_pos
            except Exception:
                return value
            return value

        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update edge paths only in safe, live state
            try:
                if not getattr(self, "_ready_scene_ops", False):
                    return super().itemChange(change, value)
                ed = getattr(self, "editor", None)
                if ed is None or not getattr(ed, "_alive", True) or getattr(ed, "_closing", False):
                    return super().itemChange(change, value)
                self._prev_pos = self.pos()
                for e in list(self._edges):
                    if not _qt_is_valid(e):
                        continue
                    # Deep validity check for ports before path update
                    sp = getattr(e, "src_port", None)
                    dp = getattr(e, "dst_port", None)
                    if not (_qt_is_valid(sp) and _qt_is_valid(dp)):
                        continue
                    if not (_qt_is_valid(getattr(sp, "node_item", None)) and _qt_is_valid(getattr(dp, "node_item", None))):
                        continue
                    e.update_path()
            except Exception:
                pass
            return super().itemChange(change, value)

        if change == QGraphicsItem.ItemSelectedHasChanged:
            # Bring newly selected node to front as well (e.g., rubber-band selection)
            try:
                ed = getattr(self, "editor", None)
                if ed and getattr(ed, "_alive", True) and not getattr(ed, "_closing", False):
                    if self.isSelected():
                        ed.raise_node_to_top(self)
            except Exception:
                pass
            return super().itemChange(change, value)

        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        """Provide simple node context menu (rename/delete)."""
        menu = QMenu(self.editor.window())
        ss = self.editor.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)
        act_rename = QAction(self.editor.config.node_context_rename(), menu)
        act_delete = QAction(self.editor.config.node_context_delete(), menu)
        menu.addAction(act_rename)
        menu.addSeparator()
        menu.addAction(act_delete)
        chosen = menu.exec(event.screenPos())
        if chosen == act_rename:
            from PySide6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self.editor.window(), self.editor.config.rename_dialog_title(), self.editor.config.rename_dialog_label(), text=self.node.name)
            if ok and new_name:
                self.node.name = new_name
                self.update()
        elif chosen == act_delete:
            self.editor._delete_node_item(self)

    def _on_value_changed(self, prop_id: str, value):
        """Persist value into the graph model when an editor changed."""
        self.graph.set_property_value(self.node.uuid, prop_id, value)

    def detach_proxy_widget(self):
        """Detach and delete inner QWidget safely (used during teardown)."""
        try:
            if hasattr(self, "_proxy") and _qt_is_valid(self._proxy):
                try:
                    self._proxy.removeEventFilter(self)
                except Exception:
                    pass
            if hasattr(self, "_content") and _qt_is_valid(self._content):
                try:
                    self._content.removeEventFilter(self)
                except Exception:
                    pass
                try:
                    self._content.valueChanged.disconnect(self._on_value_changed)
                except Exception:
                    pass

            if hasattr(self, "_proxy") and _qt_is_valid(self._proxy):
                try:
                    self._proxy.setWidget(None)
                except Exception:
                    pass
            if hasattr(self, "_content") and _qt_is_valid(self._content):
                try:
                    self._content.setParent(None)
                    self._content.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

    def pre_cleanup(self):
        """Break internal references and signals to avoid accessing deleted Qt objects."""
        try:
            # Disconnect port signals and drop references
            for p in list(self._in_ports.values()) + list(self._out_ports.values()):
                try:
                    if _qt_is_valid(p):
                        p.portClicked.disconnect(self.editor._on_port_clicked)
                except Exception:
                    pass
            self._in_ports.clear()
            self._out_ports.clear()
        except Exception:
            pass
        try:
            # Break edges' back-references to ports
            for e in list(self._edges):
                try:
                    e.src_port = None
                    e.dst_port = None
                except Exception:
                    pass
            self._edges.clear()
        except Exception:
            pass

    def mark_ready_for_scene_ops(self, ready: bool = True):
        """Enable/disable scene-dependent operations (collision checks, edge updates)."""
        self._ready_scene_ops = bool(ready)