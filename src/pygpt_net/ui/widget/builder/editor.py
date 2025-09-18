#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Dict, Optional, List, Tuple
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QSizeF, QObject, Signal, Property, QEvent
from PySide6.QtGui import (
    QAction, QBrush, QColor, QPainter, QPainterPath, QPen, QTransform,
    QUndoStack, QUndoCommand, QPalette, QPainterPathStroker, QCursor,
    QKeySequence, QShortcut
)
from PySide6.QtWidgets import (
    QWidget, QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPathItem,
    QGraphicsObject, QGraphicsWidget, QGraphicsProxyWidget, QStyleOptionGraphicsItem,
    QMenu, QMessageBox, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QLabel
)

# Safety: check C++ pointer validity to avoid calling methods on deleted Qt objects
try:
    from shiboken6 import isValid as _qt_is_valid
except Exception:
    def _qt_is_valid(obj) -> bool:
        return obj is not None

from pygpt_net.core.builder.graph import NodeGraph, NodeTypeRegistry, NodeModel, PropertyModel, ConnectionModel
from pygpt_net.utils import trans


# ------------------------ Graphics View / Scene ------------------------

class NodeGraphicsView(QGraphicsView):
    """Zoomable, pannable view with a grid background and extra shortcuts."""
    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None):
        super().__init__(scene, parent)
        self.setRenderHints(self.renderHints() |
                            QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setFocusPolicy(Qt.StrongFocus)

        self._zoom = 1.0
        self._zoom_step = 1.15
        self._min_zoom = 0.2
        self._max_zoom = 3.0

        self._panning = False
        self._space_panning = False
        self._last_pan_pos = None

    def drawBackground(self, painter: QPainter, rect: QRectF):
        parent_editor = self.parent()  # NodeEditor
        color_back = getattr(parent_editor, "_grid_back_color", QColor(35, 35, 38))
        color_pen = getattr(parent_editor, "_grid_pen_color", QColor(55, 55, 60))
        painter.fillRect(rect, color_back)
        pen = QPen(color_pen)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        grid = 20
        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)
        x = left
        while x < rect.right():
            painter.drawLine(x, rect.top(), x, rect.bottom())
            x += grid
        y = top
        while y < rect.bottom():
            painter.drawLine(rect.left(), y, rect.right(), y)
            y += grid

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            editor = self.parent()  # NodeEditor
            if editor and getattr(editor, "_wire_state", "idle") != "idle":
                editor._dbg("ESC -> cancel interactive wire")
                editor._cancel_interactive_connection()
                e.accept()
                return

        if e.key() == Qt.Key_Space and not self._space_panning:
            self._space_panning = True
            self.setCursor(Qt.OpenHandCursor)
            e.accept()
            return
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            editor = self.parent()  # NodeEditor
            if editor and self.scene():
                editor._dbg("Key DEL/BACKSPACE pressed -> delete selected connections")
                editor._delete_selected_connections()
                e.accept()
                return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and self._space_panning:
            self._space_panning = False
            if not self._panning:
                self.setCursor(Qt.ArrowCursor)
            e.accept()
            return
        super().keyReleaseEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self._apply_zoom(self._zoom_step if e.angleDelta().y() > 0 else 1.0 / self._zoom_step)
            e.accept()
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space_panning):
            self._panning = True
            self._last_pan_pos = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._panning and self._last_pan_pos is not None:
            delta = e.position() - self._last_pan_pos
            self._last_pan_pos = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._panning and e.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._panning = False
            self.setCursor(Qt.OpenHandCursor if self._space_panning else Qt.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def zoom_in(self):
        self._apply_zoom(self._zoom_step)

    def zoom_out(self):
        self._apply_zoom(1.0 / self._zoom_step)

    def _apply_zoom(self, factor: float):
        new_zoom = self._zoom * factor
        if not (self._min_zoom <= new_zoom <= self._max_zoom):
            return
        self._zoom = new_zoom
        self.scale(factor, factor)


class NodeGraphicsScene(QGraphicsScene):
    sceneContextRequested = Signal(QPointF)
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def contextMenuEvent(self, event):
        transform = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(event.scenePos(), transform)
        if item is None:
            self.sceneContextRequested.emit(event.scenePos())
            event.accept()
            return
        super().contextMenuEvent(event)


# ------------------------ Items: Port, Edge, Node ------------------------

class PortItem(QGraphicsObject):
    radius = 6.0
    portClicked = Signal(object)   # self
    side: str  # "input" or "output"

    def __init__(self, node_item: "NodeItem", prop_id: str, side: str):
        super().__init__(node_item)
        self.node_item = node_item
        self.prop_id = prop_id
        self.side = side
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self._hover = False
        self._connected_count = 0
        self._can_accept = False
        self.setZValue(3)

    def boundingRect(self) -> QRectF:
        r = self.radius
        return QRectF(-r, -r, 2 * r, 2 * r)

    def shape(self) -> QPainterPath:
        pick_r = float(getattr(self.node_item.editor, "_port_pick_radius", 10.0)) or 10.0
        p = QPainterPath()
        p.addEllipse(QRectF(-pick_r, -pick_r, 2 * pick_r, 2 * pick_r))
        return p

    def paint(self, p: QPainter, opt: QStyleOptionGraphicsItem, widget=None):
        editor: NodeEditor = self.node_item.editor
        base = editor._port_input_color if self.side == "input" else editor._port_output_color
        color = editor._port_connected_color if self._connected_count > 0 else base
        if self._hover:
            color = color.lighter(130)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(self.boundingRect())
        if self._can_accept:
            ring = QPen(editor._port_accept_color, 3.0)
            ring.setCosmetic(True)
            p.setPen(ring)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(self.boundingRect().adjusted(-2, -2, 2, 2))

    def hoverEnterEvent(self, e):
        self._hover = True
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self._hover = False
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.node_item.editor._dbg(f"Port clicked: side={self.side}, node={self.node_item.node.name}({self.node_item.node.uuid}), prop={self.prop_id}, connected_count={self._connected_count}")
            self.portClicked.emit(self)
            e.accept()
            return
        super().mousePressEvent(e)

    def increment_connections(self, delta: int):
        self._connected_count = max(0, self._connected_count + delta)
        self.update()

    def set_accept_highlight(self, enabled: bool):
        if self._can_accept != enabled:
            self._can_accept = enabled
            self.update()


class EdgeItem(QGraphicsPathItem):
    def __init__(self, src_port: PortItem, dst_port: PortItem, temporary: bool = False):
        super().__init__()
        self.src_port = src_port
        self.dst_port = dst_port
        self.temporary = temporary
        self.setZValue(1)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self._editor = self.src_port.node_item.editor
        self._hover = False
        # drag priming (for rewire by dragging the edge)
        self._drag_primed = False
        self._drag_start_scene = QPointF()
        self._update_pen()

    def set_hovered(self, hovered: bool):
        if self._hover != hovered:
            self._hover = hovered
            self._update_pen()

    def _update_pen(self):
        color = self._editor._edge_selected_color if (self._hover or self.isSelected()) else self._editor._edge_color
        pen = QPen(color)
        pen.setWidthF(2.0 if not self.temporary else 1.5)
        pen.setStyle(Qt.SolidLine if not self.temporary else Qt.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._update_pen()
        return super().itemChange(change, value)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        width = float(getattr(self._editor, "_edge_pick_width", 12.0) or 12.0)
        stroker.setWidth(width)
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(self.path())

    def update_path(self, end_pos: Optional[QPointF] = None):
        p = QPainterPath()
        p0 = self.src_port.scenePos()
        p1 = end_pos if end_pos is not None else self.dst_port.scenePos()
        dx = abs(p1.x() - p0.x())
        c1 = QPointF(p0.x() + dx * 0.5, p0.y())
        c2 = QPointF(p1.x() - dx * 0.5, p1.y())
        p.moveTo(p0)
        p.cubicTo(c1, c2, p1)
        self.setPath(p)

    def contextMenuEvent(self, event):
        if self.temporary:
            return
        self._editor._dbg(f"Edge context menu on edge id={id(self)}")
        menu = QMenu(self._editor.window())
        ss = self._editor.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)
        act_del = QAction("Delete connection", menu)
        menu.addAction(act_del)
        chosen = menu.exec(event.screenPos())
        if chosen == act_del:
            self._editor._dbg(f"Context DELETE on edge id={id(self)}")
            self._editor._delete_edge(self)

    # --- drag-based rewire priming on the edge ---

    def mousePressEvent(self, e):
        if not self.temporary and e.button() == Qt.LeftButton:
            if not self.isSelected():
                self.setSelected(True)
            self._drag_primed = True
            self._drag_start_scene = e.scenePos()
            self._editor._dbg(f"Edge LMB press -> primed drag, edge id={id(self)}")
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not self.temporary and self._drag_primed:
            dist = abs(e.scenePos().x() - self._drag_start_scene.x()) + abs(e.scenePos().y() - self._drag_start_scene.y())
            if dist > 6 and getattr(self._editor, "_wire_state", "idle") == "idle":
                self._editor._dbg(f"Edge drag start -> begin REWIRE from EDGE (move dst), edge id={id(self)}")
                self._editor._start_rewire_from_edge(self, e.scenePos())
                self._drag_primed = False
                e.accept()
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_primed = False
        super().mouseReleaseEvent(e)


class NodeContentWidget(QWidget):
    valueChanged = Signal(str, object)
    def __init__(self, node: NodeModel, graph: NodeGraph, editor: "NodeEditor", parent: Optional[QWidget] = None):
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
            w: QWidget
            if pm.type == "str":
                w = QLineEdit()
                if pm.value is not None:
                    w.setText(str(pm.value))
                w.setReadOnly(not pm.editable)
                w.textEdited.connect(lambda v, pid=pid: self.valueChanged.emit(pid, v))
            elif pm.type == "int":
                w = QSpinBox()
                w.setRange(-10**9, 10**9)
                if pm.value is not None:
                    w.setValue(int(pm.value))
                w.setEnabled(pm.editable)
                w.valueChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, int(v)))
            elif pm.type == "float":
                w = QDoubleSpinBox()
                w.setDecimals(4)
                w.setRange(-1e12, 1e12)
                if pm.value is not None:
                    w.setValue(float(pm.value))
                w.setEnabled(pm.editable)
                w.valueChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, float(v)))
            elif pm.type == "bool":
                w = QCheckBox()
                if pm.value:
                    w.setChecked(bool(pm.value))
                w.setEnabled(pm.editable)
                w.toggled.connect(lambda v, pid=pid: self.valueChanged.emit(pid, bool(v)))
            elif pm.type == "combo":
                w = QComboBox()
                for opt in (pm.options or []):
                    w.addItem(opt)
                if pm.value is not None and pm.value in (pm.options or []):
                    w.setCurrentText(pm.value)
                w.setEnabled(pm.editable)
                w.currentTextChanged.connect(lambda v, pid=pid: self.valueChanged.emit(pid, v))
            else:
                w = QLabel("-")
                w.setEnabled(False)
            self.form.addRow(pm.name, w)
            self._editors[pid] = w


class NodeItem(QGraphicsWidget):
    """Rounded node with title and ports aligned to property rows."""
    def __init__(self, editor: "NodeEditor", node: NodeModel):
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

        # --- Resize state ---
        self.setAcceptHoverEvents(True)
        self.setFiltersChildEvents(True)  # receive hover also when over children (proxy/ports)
        self._resizing: bool = False
        self._resize_mode: str = "none"   # "none" | "right" | "bottom" | "corner"
        self._resize_press_local = QPointF()
        self._resize_start_size = QSizeF()
        self._hover_resize_mode: str = "none"

        self._sync_size()
        self._build_ports()
        self._sync_size()

    # ---------- Size helpers ----------
    def _effective_hit_margin(self) -> float:
        # Active resize zone width computed from visual margin minus hit inset
        margin = float(getattr(self.editor, "_resize_grip_margin", 12.0) or 12.0)
        inset = float(getattr(self.editor, "_resize_grip_hit_inset", 3.0) or 0.0)
        hit = max(4.0, margin - inset)  # never less than 4px
        return hit

    def _min_size_from_content(self) -> QSizeF:
        csz = self._content.sizeHint() if _qt_is_valid(self._content) else QSizeF(120, 40)
        hit = self._effective_hit_margin()
        w = max(80.0, float(csz.width()) + 16.0 + hit)
        h_auto = float(csz.height()) + 16.0 + float(self._title_height) + hit
        h = max(float(self._title_height + 16 + hit), h_auto)
        return QSizeF(w, h)

    def _apply_resize(self, new_size: QSizeF, clamp: bool = True):
        hit = self._effective_hit_margin()
        minsz = self._min_size_from_content() if clamp else QSizeF(0.0, 0.0)
        w = max(minsz.width(), float(new_size.width()))
        h = max(minsz.height(), float(new_size.height()))
        self.resize(QSizeF(w, h))
        # Right and bottom gutters = 'hit' (active zone and space for indicators)
        ph = max(0.0, h - self._title_height - hit)
        pw = max(0.0, w - hit)
        if _qt_is_valid(self._proxy):
            try:
                self._proxy.resize(pw, ph)
            except Exception:
                pass
        self.update_ports_positions()
        self.update()

    def _sync_size(self):
        csz = self._content.sizeHint()
        hit = self._effective_hit_margin()
        w = float(csz.width()) + 16.0 + hit
        auto_h = float(csz.height()) + 16.0 + float(self._title_height) + hit
        h = max(auto_h, float(self._title_height + 16 + hit))
        self.resize(QSizeF(w, h))
        self._proxy.resize(max(0.0, w - hit), max(0.0, h - self._title_height - hit))

    def _build_ports(self):
        yoff = self._title_height + 8
        row_h = 24
        for pid, pm in self.node.properties.items():
            if pm.allowed_inputs != 0:
                p = PortItem(self, pid, "input")
                p.setPos(-10, yoff + 8)
                p.portClicked.connect(self.editor._on_port_clicked)
                self._in_ports[pid] = p
            if pm.allowed_outputs != 0:
                p = PortItem(self, pid, "output")
                p.setPos(self.size().width() + 10, yoff + 8)
                p.portClicked.connect(self.editor._on_port_clicked)
                self._out_ports[pid] = p
            yoff += row_h

    def update_ports_positions(self):
        yoff = self._title_height + 8
        row_h = 24
        for pid in self.node.properties.keys():
            if pid in self._in_ports:
                self._in_ports[pid].setPos(-10, yoff + 8)
            if pid in self._out_ports:
                self._out_ports[pid].setPos(self.size().width() + 10, yoff + 8)
            yoff += row_h
        for e in self._edges:
            e.update_path()

    def add_edge(self, edge: EdgeItem):
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge(self, edge: EdgeItem):
        if edge in self._edges:
            self._edges.remove(edge)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.size().width(), self.size().height())

    def _hit_resize_zone(self, pos: QPointF) -> str:
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

    def paint(self, p: QPainter, opt: QStyleOptionGraphicsItem, widget=None):
        r = self.boundingRect()
        path = QPainterPath()
        path.addRoundedRect(r, self._radius, self._radius)
        p.setRenderHint(QPainter.Antialiasing, True)
        bg = self.editor._node_bg_color
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

        # --- Resize indicator and hover highlight ---
        hit = self._effective_hit_margin()
        mode = self._resize_mode if self._resizing else self._hover_resize_mode
        hl = QColor(border)
        hl.setAlpha(110)
        if mode in ("right", "corner"):
            p.fillRect(QRectF(r.right() - hit, r.top() + self._title_height, hit, r.height() - self._title_height), hl)
        if mode in ("bottom", "corner"):
            p.fillRect(QRectF(r.left(), r.bottom() - hit, r.width(), hit), hl)

        # Corner triangle + hatch (drawn inside the "hit" zone)
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

    # ---------- Mouse/hover for drag vs resize ----------

    def _apply_hover_from_pos(self, pos: QPointF):
        mode = self._hit_resize_zone(pos)
        if mode != self._hover_resize_mode and not self._resizing:
            self._hover_resize_mode = mode
            if mode == "corner":
                self.setCursor(Qt.SizeFDiagCursor)
            elif mode == "right":
                self.setCursor(Qt.SizeHorCursor)
            elif mode == "bottom":
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.unsetCursor()
            self.update()

    def hoverMoveEvent(self, event):
        view = self.editor.view
        if getattr(view, "_space_panning", False) or getattr(view, "_panning", False):
            self._hover_resize_mode = "none"
            self.unsetCursor()
            self.update()
            return super().hoverMoveEvent(event)

        self._apply_hover_from_pos(event.pos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._resizing:
            self._hover_resize_mode = "none"
            self.unsetCursor()
            self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            mode = self._hit_resize_zone(event.pos())
            if mode != "none":
                # start resize
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

            # else -> start normal drag
            self._dragging = True
            self._overlaps = False
            self._start_pos = QPointF(self.pos())
            self._last_valid_pos = QPointF(self.pos())
            self._z_before_drag = self.zValue()
            self.setZValue(self._z_before_drag + 100)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
            # even when hoverMove isn't delivered (e.g., over children), child filters will end up here
            self._apply_hover_from_pos(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing and event.button() == Qt.LeftButton:
            self._resizing = False
            self.setZValue(self._z_before_drag)
            # refresh hover after finishing resize (cursor may still be over the item)
            self._apply_hover_from_pos(event.pos())
            new_size = QSizeF(self.size())
            if abs(new_size.width() - self._resize_start_size.width()) > 0.5 or \
               abs(new_size.height() - self._resize_start_size.height()) > 0.5:
                self.editor._undo.push(ResizeNodeCommand(self, self._resize_start_size, new_size))
            self._resize_mode = "none"
            event.accept()
            return

        if self._dragging and event.button() == Qt.LeftButton:
            if self._overlaps:
                self.setPos(self._last_valid_pos)
            else:
                if self.pos() != self._start_pos:
                    self.editor._undo.push(MoveNodeCommand(self, self._start_pos, self.pos()))
            self.setOpacity(1.0)
            self.setZValue(self._z_before_drag)
            self._dragging = False
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, e):
        et = e.type()
        try:
            # 1) Mouse move over QGraphicsProxyWidget (content area)
            if obj is self._proxy and et in (QEvent.GraphicsSceneMouseMove, QEvent.GraphicsSceneHoverMove):
                local = self.mapFromScene(e.scenePos())
                self._apply_hover_from_pos(local)
                return False
            if obj is self._proxy and et == QEvent.GraphicsSceneHoverLeave:
                # leaving proxy -> if not resizing, clear hover
                if not self._resizing:
                    self._hover_resize_mode = "none"
                    self.unsetCursor()
                    self.update()
                return False

            # 2) Mouse move over inner QWidget (inside the proxy)
            if obj is self._content and et in (QEvent.MouseMove, QEvent.HoverMove, QEvent.Enter):
                # map QPoint from QWidget to NodeItem local coordinates
                if hasattr(e, "position"):  # Qt6 mouse event
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
                return False
        except Exception:
            pass
        return False

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos: QPointF = value
            sc = self.scene()
            if sc is not None:
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
                self.setOpacity(0.5 if overlap else 1.0)
                if not overlap:
                    self._last_valid_pos = new_pos
            return value
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._prev_pos = self.pos()
            for e in list(self._edges):
                e.update_path()
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu(self.editor.window())
        ss = self.editor.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)
        act_rename = QAction("Rename", menu)
        act_delete = QAction("Delete", menu)
        menu.addAction(act_rename)
        menu.addSeparator()
        menu.addAction(act_delete)
        chosen = menu.exec(event.screenPos())
        if chosen == act_rename:
            from PySide6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self.editor.window(), "Rename Node", "Name:", text=self.node.name)
            if ok and new_name:
                self.node.name = new_name
                self.update()
        elif chosen == act_delete:
            self.editor._delete_node_item(self)

    def _on_value_changed(self, prop_id: str, value):
        self.graph.set_property_value(self.node.uuid, prop_id, value)

    # ---- Safe detach for proxy/widget to avoid crashes on dialog close ----
    def detach_proxy_widget(self):
        try:
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


# ------------------------ Undo/Redo Commands ------------------------

class AddNodeCommand(QUndoCommand):
    def __init__(self, editor: "NodeEditor", type_name: str, scene_pos: QPointF):
        super().__init__(f"Add {type_name}")
        self.editor = editor
        self.type_name = type_name
        self.scene_pos = scene_pos
        self._node_uuid: Optional[str] = None

    def redo(self):
        if self._node_uuid is None:
            node = self.editor.graph.create_node_from_type(self.type_name)
            self._node_uuid = node.uuid
            self.editor._add_node_model(node, self.scene_pos)
        else:
            node = self.editor._model_by_uuid(self._node_uuid)
            self.editor._add_node_item(node, self.scene_pos)

    def undo(self):
        if self._node_uuid:
            self.editor._remove_node_by_uuid(self._node_uuid)


class MoveNodeCommand(QUndoCommand):
    def __init__(self, item: NodeItem, old_pos: QPointF, new_pos: QPointF):
        super().__init__("Move Node")
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos

    def redo(self):
        self.item.setPos(self.new_pos)

    def undo(self):
        self.item.setPos(self.old_pos)


class ResizeNodeCommand(QUndoCommand):
    def __init__(self, item: NodeItem, old_size: QSizeF, new_size: QSizeF):
        super().__init__("Resize Node")
        self.item = item
        self.old_size = QSizeF(old_size)
        self.new_size = QSizeF(new_size)

    def redo(self):
        self.item._apply_resize(self.new_size, clamp=True)

    def undo(self):
        self.item._apply_resize(self.old_size, clamp=True)


class ConnectCommand(QUndoCommand):
    def __init__(self, editor: "NodeEditor", src: PortItem, dst: PortItem):
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
        if self._conn_uuid:
            self.editor._dbg(f"ConnectCommand.undo -> remove uuid={self._conn_uuid}")
            self.editor._remove_connection_by_uuid(self._conn_uuid)


class RewireConnectionCommand(QUndoCommand):
    """Replace an existing connection with a new one (or delete it). Single undoable step."""
    def __init__(self, editor: "NodeEditor",
                 old_conn: ConnectionModel,
                 new_src: Optional[PortItem],
                 new_dst: Optional[PortItem]):
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
        self.editor._dbg(f"RewireCommand.undo -> restore old={self.old_uuid}, remove new={self._new_uuid}")
        if not self._applied:
            return
        if self._new_uuid:
            self.editor._remove_connection_by_uuid(self._new_uuid)
        old = ConnectionModel.from_dict(self.old_conn_data)
        self.editor.graph.add_connection(old)


class ClearGraphCommand(QUndoCommand):
    def __init__(self, editor: "NodeEditor"):
        super().__init__("Clear")
        self.editor = editor
        self._snapshot: Optional[dict] = None

    def redo(self):
        if self._snapshot is None:
            self._snapshot = self.editor.graph.to_dict()
        self.editor._dbg("ClearGraph.redo -> clearing scene+graph")
        self.editor._clear_scene_and_graph()

    def undo(self):
        self._dbg = self.editor._dbg
        self._dbg("ClearGraph.undo -> restoring snapshot")
        if self._snapshot:
            self.editor.load_layout(self._snapshot)


# ------------------------ NodeEditor ------------------------

class NodeEditor(QWidget):
    """Main widget embedding a QGraphicsView-based node editor."""
    def _q_set(self, name, value):
        setattr(self, name, value)
        self._update_theme()

    def _q_set_bool(self, name, value: bool):
        setattr(self, name, bool(value))

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

    _edge_pick_width: float = 12.0
    _resize_grip_margin: float = 12.0
    _resize_grip_hit_inset: float = 5.0
    _port_pick_radius: float = 10.0
    _port_click_rewire_if_connected: bool = True
    _rewire_drop_deletes: bool = True

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

    edgePickWidth = Property(float, lambda self: self._edge_pick_width, lambda self, v: self._set_edge_pick_width(v))
    resizeGripMargin = Property(float, lambda self: self._resize_grip_margin, lambda self, v: self._q_set("_resize_grip_margin", float(v)))
    resizeGripHitInset = Property(float, lambda self: self._resize_grip_hit_inset, lambda self, v: self._set_resize_grip_hit_inset(float(v)))
    portPickRadius = Property(float, lambda self: self._port_pick_radius, lambda self, v: self._q_set("_port_pick_radius", float(v)))
    portClickRewireIfConnected = Property(bool, lambda self: self._port_click_rewire_if_connected, lambda self, v: self._q_set_bool("_port_click_rewire_if_connected", v))
    rewireDropDeletes = Property(bool, lambda self: self._rewire_drop_deletes, lambda self, v: self._q_set_bool("_rewire_drop_deletes", v))

    def _set_resize_grip_hit_inset(self, v: float):
        self._resize_grip_hit_inset = max(0.0, float(v))
        # recompute proxy sizes/gutters
        for item in list(self._uuid_to_item.values()):
            if _qt_is_valid(item):
                item._apply_resize(item.size(), clamp=True)
        self.view.viewport().update()

    def _set_edge_pick_width(self, v: float):
        self._edge_pick_width = float(v) if v and v > 0 else 12.0
        for edge in list(self._conn_uuid_to_edge.values()):
            if _qt_is_valid(edge):
                edge.prepareGeometryChange()
                edge.update()
        if getattr(self, "_interactive_edge", None) and _qt_is_valid(self._interactive_edge):
            self._interactive_edge.prepareGeometryChange()
            self._interactive_edge.update()
        self.view.viewport().update()

    def __init__(self, parent: Optional[QWidget] = None, registry: Optional[NodeTypeRegistry] = None):
        super().__init__(parent)
        self.setObjectName("NodeEditor")
        self._debug = False  # DEBUG toggle
        self._dbg("INIT NodeEditor")

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

        # Wire interaction state: idle | drawing | rewire-primed | rewiring
        self._wire_state: str = "idle"
        self._rewire_conn_uuid: Optional[str] = None
        self._rewire_hidden_edge: Optional[EdgeItem] = None
        self._rewire_fixed_src: Optional[PortItem] = None
        self._rewire_press_scene_pos: Optional[QPointF] = None

        self._spawn_origin: Optional[QPointF] = None
        self._spawn_index: int = 0

        self._saved_drag_mode: Optional[QGraphicsView.DragMode] = None

        self._shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self._shortcut_delete.setContext(Qt.ApplicationShortcut)
        self._shortcut_delete.activated.connect(self._delete_selected_connections)
        self._shortcut_backspace = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        self._shortcut_backspace.setContext(Qt.ApplicationShortcut)
        self._shortcut_backspace.activated.connect(self._delete_selected_connections)

        self.scene.sceneContextRequested.connect(self._on_scene_context_menu)
        self.graph.nodeAdded.connect(self._on_graph_node_added)
        self.graph.nodeRemoved.connect(self._on_graph_node_removed)
        self.graph.connectionAdded.connect(self._on_graph_connection_added)
        self.graph.connectionRemoved.connect(self._on_graph_connection_removed)
        self.graph.cleared.connect(self._on_graph_cleared)

        self.scene.installEventFilter(self)

        self._alive = True
        self.destroyed.connect(self._on_destroyed)

        self.on_clear = None

    # ---------- Debug helper ----------
    def _dbg(self, msg: str):
        if self._debug:
            print(f"[NodeEditor][{hex(id(self))}] {msg}")

    # ---------- QWidget overrides ----------

    def _on_destroyed(self):
        self._alive = False
        try:
            if _qt_is_valid(self.scene):
                self.scene.removeEventFilter(self)
        except Exception:
            pass
        self._cleanup_node_proxies()
        self._disconnect_graph_signals()

    def closeEvent(self, e):
        self._dbg("closeEvent -> full cleanup")
        try:
            self._shortcut_delete.setEnabled(False)
            self._shortcut_backspace.setEnabled(False)
        except Exception:
            pass
        self._reset_interaction_states(remove_hidden_edges=True)
        try:
            self.scene.removeEventFilter(self)
        except Exception:
            pass
        self._disconnect_graph_signals()
        self._cleanup_node_proxies()
        try:
            self.view.setScene(None)
        except Exception:
            pass
        try:
            self._remove_all_edge_items_from_scene()
            self.scene.clear()
        except Exception:
            pass
        self._alive = False
        super().closeEvent(e)

    def _disconnect_graph_signals(self):
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
        self.view.setGeometry(self.rect())
        super().resizeEvent(e)

    def showEvent(self, e):
        if self._spawn_origin is None and self.view:
            self._spawn_origin = self.view.mapToScene(self.view.viewport().rect().center())
        self._reapply_stylesheets()
        super().showEvent(e)

    def event(self, e):
        et = e.type()
        if et in (QEvent.StyleChange, QEvent.PaletteChange, QEvent.FontChange,
                  QEvent.ApplicationPaletteChange, QEvent.ApplicationFontChange):
            self._reapply_stylesheets()
        if et in (QEvent.FocusOut, QEvent.WindowDeactivate):
            self._dbg("event -> focus out/window deactivate -> reset interaction")
            self._reset_interaction_states(remove_hidden_edges=False)
        return super().event(e)

    # ---------- Public API ----------

    def add_node(self, type_name: str, scene_pos: QPointF):
        self._undo.push(AddNodeCommand(self, type_name, scene_pos))

    def clear(self, ask_user: bool = True):
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
        self._undo.undo()

    def redo(self):
        self._undo.redo()

    def save_layout(self) -> dict:
        """Serialize graph plus per-node positions and sizes."""
        data = self.graph.to_dict()
        data["positions"] = {
            nuuid: [self._uuid_to_item[nuuid].pos().x(), self._uuid_to_item[nuuid].pos().y()]
            for nuuid in self._uuid_to_item
        }
        data["sizes"] = {
            nuuid: [float(self._uuid_to_item[nuuid].size().width()),
                    float(self._uuid_to_item[nuuid].size().height())]
            for nuuid in self._uuid_to_item
        }
        return data

    def load_layout(self, data: dict):
        """Reset and restore graph + positions and (optionally) sizes."""
        self._dbg("load_layout -> reset and from_dict")
        self._reset_interaction_states(remove_hidden_edges=True)
        self._clear_scene_only(hard=True)
        self.graph.from_dict(data)

        positions = data.get("positions", {})
        sizes = data.get("sizes", {})

        # Apply sizes first (so port geometry is correct), then positions.
        for nuuid, wh in sizes.items():
            item = self._uuid_to_item.get(nuuid)
            if item and isinstance(wh, (list, tuple)) and len(wh) == 2:
                try:
                    w = float(wh[0]); h = float(wh[1])
                    item._apply_resize(QSizeF(w, h), clamp=True)
                except Exception:
                    pass

        for nuuid, xy in positions.items():
            item = self._uuid_to_item.get(nuuid)
            if item and isinstance(xy, (list, tuple)) and len(xy) == 2:
                try:
                    item.setPos(QPointF(float(xy[0]), float(xy[1])))
                except Exception:
                    pass

        # Make sure edges are updated to final geometry.
        for item in self._uuid_to_item.values():
            if _qt_is_valid(item):
                item.update_ports_positions()

        self._reapply_stylesheets()
        self.center_on_content()

    def export_schema(self) -> dict:
        return self.graph.to_schema()

    def debug_state(self) -> dict:
        return self.save_layout()

    def zoom_in(self):
        self.view.zoom_in()

    def zoom_out(self):
        self.view.zoom_out()

    # ---------- Graph <-> UI sync ----------

    def _model_by_uuid(self, node_uuid: str) -> Optional[NodeModel]:
        return self.graph.nodes.get(node_uuid)

    def _on_graph_node_added(self, node: NodeModel):
        if node.uuid in self._uuid_to_item:
            return
        pos = self._pending_node_positions.pop(node.uuid, None)
        if pos is None:
            pos = self._next_spawn_pos()
        self._dbg(f"graph.nodeAdded -> add item for node={node.name}({node.uuid}) at {pos}")
        self._add_node_item(node, pos)

    def _on_graph_node_removed(self, node_uuid: str):
        self._dbg(f"graph.nodeRemoved -> remove item for node={node_uuid}")
        item = self._uuid_to_item.pop(node_uuid, None)
        if item and _qt_is_valid(item):
            try:
                self.scene.removeItem(item)
            except Exception:
                pass

    def _on_graph_connection_added(self, conn: ConnectionModel):
        self._dbg(f"graph.connectionAdded -> add edge uuid={conn.uuid} src=({conn.src_node},{conn.src_prop}) dst=({conn.dst_node},{conn.dst_prop})")
        self._add_edge_for_connection(conn)

    def _on_graph_connection_removed(self, conn_uuid: str):
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
        self._dbg("graph.cleared -> clear scene only")
        self._reset_interaction_states(remove_hidden_edges=True)
        self._clear_scene_only(hard=True)

    # ---------- Scene helpers ----------

    def _scene_to_global(self, scene_pos: QPointF) -> QPoint:
        from PySide6.QtCore import QPoint as _QPoint
        vp_pt = self.view.mapFromScene(scene_pos)
        if isinstance(vp_pt, QPointF):
            vp_pt = _QPoint(int(vp_pt.x()), int(vp_pt.y()))
        return self.view.viewport().mapToGlobal(vp_pt)

    def _on_scene_context_menu(self, scene_pos: QPointF):
        menu = QMenu(self.window())
        ss = self.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)

        add_menu = menu.addMenu("Add")
        action_by_type: Dict[QAction, str] = {}
        for tname in self.graph.registry.types():
            act = add_menu.addAction(tname)
            action_by_type[act] = tname

        menu.addSeparator()
        act_undo = QAction("Undo", menu)
        act_redo = QAction("Redo", menu)
        act_clear = QAction("Clear", menu)
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

    # ---------- Add/remove nodes/edges ----------

    def _add_node_model(self, node: NodeModel, scene_pos: QPointF):
        self._pending_node_positions[node.uuid] = scene_pos
        self.graph.add_node(node)

    def _add_node_item(self, node: NodeModel, scene_pos: QPointF):
        item = NodeItem(self, node)
        self.scene.addItem(item)
        free_pos = self._find_free_position(scene_pos, item.size())
        item.setPos(free_pos)
        item.update_ports_positions()
        self._uuid_to_item[node.uuid] = item
        self._apply_styles_to_content(item._content)

    def _find_free_position(self, desired: QPointF, size: QSizeF, step: int = 40, max_rings: int = 20) -> QPointF:
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
        if self._spawn_origin is None:
            if not self.view.viewport().rect().isEmpty():
                self._spawn_origin = self.view.mapToScene(self.view.viewport().rect().center())
            else:
                self._spawn_origin = self.scene.sceneRect().center()
        origin = self._spawn_origin
        step = 80
        base_grid = [(-1, -1), (0, -1), (1, -1),
                     (-1,  0), (0,  0), (1,  0),
                     (-1,  1), (0,  1), (1,  1)]
        ring = self._spawn_index // len(base_grid) + 1
        gx, gy = base_grid[self._spawn_index % len(base_grid)]
        self._spawn_index += 1
        return QPointF(origin.x() + gx * step * ring, origin.y() + gy * step * ring)

    def _remove_node_by_uuid(self, node_uuid: str):
        self.graph.remove_node(node_uuid)

    def _add_edge_for_connection(self, conn: ConnectionModel):
        # Anti-dup guard
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
        self._dbg(f"_remove_connection_by_uuid -> {conn_uuid}")
        self.graph.remove_connection(conn_uuid)

    # ---------- Theming helpers ----------

    def _update_theme(self):
        self._dbg("_update_theme")
        for item in self._uuid_to_item.values():
            if _qt_is_valid(item):
                item._apply_resize(item.size(), clamp=True)
                item.update()
        for edge in self._conn_uuid_to_edge.values():
            if _qt_is_valid(edge):
                edge._update_pen()
                edge.update()
        self.view.viewport().update()
        self._reapply_stylesheets()

    def _current_stylesheet(self) -> str:
        wnd = self.window()
        if isinstance(wnd, QWidget) and wnd.styleSheet():
            return wnd.styleSheet()
        if QApplication.instance() and QApplication.instance().styleSheet():
            return QApplication.instance().styleSheet()
        return ""

    def _current_palette(self) -> QPalette:
        wnd = self.window()
        if isinstance(wnd, QWidget):
            return wnd.palette()
        return QApplication.instance().palette() if QApplication.instance() else self.palette()

    def _apply_styles_to_content(self, content_widget: QWidget):
        if content_widget is None:
            return
        content_widget.setAttribute(Qt.WA_StyledBackground, True)
        stylesheet = self._current_stylesheet()
        pal = self._current_palette()
        content_widget.setPalette(pal)
        if stylesheet:
            content_widget.setStyleSheet(stylesheet)
        content_widget.ensurePolished()
        for w in content_widget.findChildren(QWidget):
            w.ensurePolished()

    def _reapply_stylesheets(self):
        stylesheet = self._current_stylesheet()
        pal = self._current_palette()
        for item in self._uuid_to_item.values():
            if item._content and _qt_is_valid(item._content):
                item._content.setPalette(pal)
                if stylesheet:
                    item._content.setStyleSheet(stylesheet)
                item._content.ensurePolished()
                for w in item._content.findChildren(QWidget):
                    w.ensurePolished()

    # ---------- Edge/Port helpers + rewire-aware validation ----------

    def _edges_for_port(self, port: PortItem) -> List[EdgeItem]:
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
        res = (getattr(port, "_connected_count", 0) > 0) or bool(self._edges_for_port(port))
        self._dbg(f"_port_has_connections: port={port.prop_id}/{port.side} -> {res}")
        return res

    def _choose_edge_near_cursor(self, edges: List[EdgeItem], cursor_scene: QPointF, ref_port: PortItem) -> Optional[EdgeItem]:
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

    def _can_connect_during_rewire(self, src: PortItem, dst: PortItem) -> bool:
        try:
            src_node = self.graph.nodes.get(src.node_item.node.uuid)
            dst_node = self.graph.nodes.get(dst.node_item.node.uuid)
            if not src_node or not dst_node:
                return False
            sp = src_node.properties.get(src.prop_id)
            dp = dst_node.properties.get(dst.prop_id)
            if not sp or not dp:
                return False
            if sp.allowed_outputs == 0 or dp.allowed_inputs == 0:
                return False
            if sp.type != dp.type:
                return False
            skip_uuid = self._rewire_conn_uuid
            src_count = sum(1 for c in self.graph.connections.values()
                            if c.src_node == src.node_item.node.uuid and c.src_prop == src.prop_id and c.uuid != skip_uuid)
            dst_count = sum(1 for c in self.graph.connections.values()
                            if c.dst_node == dst.node_item.node.uuid and c.dst_prop == dst.prop_id and c.uuid != skip_uuid)
            if sp.allowed_outputs > 0 and src_count >= sp.allowed_outputs:
                return False
            if dp.allowed_inputs > 0 and dst_count >= dp.allowed_inputs:
                return False
            return True
        except Exception:
            return False

    def _can_connect_for_interaction(self, src: PortItem, dst: PortItem) -> bool:
        if self._wire_state in ("rewiring", "rewire-primed"):
            return self._can_connect_during_rewire(src, dst)
        ok, _ = self.graph.can_connect((src.node_item.node.uuid, src.prop_id),
                                       (dst.node_item.node.uuid, dst.prop_id))
        return ok

    def _find_compatible_port_at(self, scene_pos: QPointF, radius: Optional[float] = None) -> Optional[PortItem]:
        if self._interactive_src_port is None:
            return None
        src = self._interactive_src_port
        pick_r_cfg = float(getattr(self, "_port_pick_radius", 10.0) or 10.0)
        pick_r = float(radius) if radius is not None else max(18.0, pick_r_cfg + 10.0)
        rect = QRectF(scene_pos.x() - pick_r, scene_pos.y() - pick_r, 2 * pick_r, 2 * pick_r)
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
            d2 = dx*dx + dy*dy
            if d2 < best_d2:
                best_d2 = d2
                best = it
        if best:
            self._dbg(f"_find_compatible_port_at: FOUND port={best.prop_id}/{best.side} on node={best.node_item.node.name}")
        return best

    # ---------- Wire interaction (new + rewire) ----------

    def _enter_wire_drag_mode(self):
        try:
            self._saved_drag_mode = self.view.dragMode()
            self.view.setDragMode(QGraphicsView.NoDrag)
        except Exception:
            self._saved_drag_mode = None

    def _leave_wire_drag_mode(self):
        if self._saved_drag_mode is not None:
            try:
                self.view.setDragMode(self._saved_drag_mode)
            except Exception:
                pass
        self._saved_drag_mode = None

    def _on_port_clicked(self, port: PortItem):
        self._dbg(f"_on_port_clicked: side={port.side}, prop={port.prop_id}, connected={self._port_has_connections(port)}")
        mods = QApplication.keyboardModifiers()
        force_new = bool(mods & Qt.ShiftModifier)
        if not force_new and self._port_has_connections(port):
            cursor_scene = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
            edges = self._edges_for_port(port)
            edge = self._choose_edge_near_cursor(edges, cursor_scene, port)
            if edge:
                self._prime_rewire_from_conn(port, getattr(edge, "_conn_uuid", None), edge, cursor_scene)
                return
        self._start_draw(port)

    def _prime_rewire_from_conn(self, origin_port: PortItem, conn_uuid: Optional[str],
                                edge: Optional[EdgeItem], press_scene_pos: QPointF):
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
        if self._wire_state != "idle":
            return
        self._wire_state = "drawing"
        self._interactive_src_port = src_port
        self._interactive_edge = EdgeItem(src_port=src_port, dst_port=src_port, temporary=True)
        self.scene.addItem(self._interactive_edge)
        self._interactive_edge.update_path(src_port.scenePos())
        self._enter_wire_drag_mode()

    def _start_rewire_from_edge(self, edge: EdgeItem, cursor_scene_pos: QPointF):
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
        if a.side == "output" and b.side == "input":
            return a, b
        if a.side == "input" and b.side == "output":
            return b, a
        return None, None

    def _set_hover_candidate(self, port: Optional[PortItem]):
        if self._hover_candidate is port:
            return
        if self._hover_candidate is not None and _qt_is_valid(self._hover_candidate):
            self._hover_candidate.set_accept_highlight(False)
        self._hover_candidate = port
        if self._hover_candidate is not None and _qt_is_valid(self._hover_candidate):
            self._hover_candidate.set_accept_highlight(True)

    def eventFilter(self, obj, event):
        if not self._alive:
            return False
        if obj is self.scene:
            et = event.type()

            if self._wire_state == "rewire-primed" and et == QEvent.GraphicsSceneMouseMove:
                pos = event.scenePos()
                if self._rewire_press_scene_pos is not None:
                    dist = abs(pos.x() - self._rewire_press_scene_pos.x()) + abs(pos.y() - self._rewire_press_scene_pos.y())
                else:
                    dist = 9999
                if dist > 6 and self._rewire_fixed_src is not None:
                    if self._rewire_hidden_edge and _qt_is_valid(self._rewire_hidden_edge):
                        self._rewire_hidden_edge.setVisible(False)
                    self._interactive_edge = EdgeItem(src_port=self._rewire_fixed_src,
                                                       dst_port=self._rewire_fixed_src,
                                                       temporary=True)
                    self.scene.addItem(self._interactive_edge)
                    self._interactive_edge.update_path(end_pos=pos)
                    self._enter_wire_drag_mode()
                    self._wire_state = "rewiring"
                    candidate = self._find_compatible_port_at(pos, radius=28.0)
                    self._set_hover_candidate(candidate)
                    return True

            if self._interactive_edge is not None and et == QEvent.GraphicsSceneMouseMove:
                pos = event.scenePos()
                if _qt_is_valid(self._interactive_edge):
                    self._interactive_edge.update_path(end_pos=pos)
                candidate = self._find_compatible_port_at(pos, radius=28.0)
                self._set_hover_candidate(candidate)
                return True

            if self._interactive_edge is not None and et == QEvent.GraphicsSceneMousePress and event.button() == Qt.RightButton:
                self._cancel_interactive_connection()
                return True

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

    # -------- Interaction reset helpers --------

    def _reset_interaction_states(self, remove_hidden_edges: bool):
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
        self._reset_interaction_states(remove_hidden_edges=False)

    def _cancel_interactive_connection(self):
        self._reset_interaction_states(remove_hidden_edges=False)

    # ---------- Delete helpers ----------

    def _detach_edge_item(self, edge: EdgeItem):
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
        conn_uuid = getattr(edge, "_conn_uuid", None)
        exists = bool(conn_uuid and conn_uuid in self.graph.connections)
        if exists:
            self._remove_connection_by_uuid(conn_uuid)
        else:
            self._detach_edge_item(edge)

    def _delete_selected_connections(self):
        if not _qt_is_valid(self.scene):
            return
        for it in list(self.scene.selectedItems()):
            if isinstance(it, EdgeItem):
                self._delete_edge(it)
        self.view.viewport().update()

    # ---------- Clear helpers required by load/close ----------

    def _remove_all_edge_items_from_scene(self):
        if not _qt_is_valid(self.scene):
            return
        for it in list(self.scene.items()):
            if isinstance(it, EdgeItem):
                try:
                    self.scene.removeItem(it)
                except Exception:
                    pass

    def _cleanup_node_proxies(self):
        for item in list(self._uuid_to_item.values()):
            try:
                if _qt_is_valid(item):
                    item.detach_proxy_widget()
            except Exception:
                pass

    def _clear_scene_only(self, hard: bool = False):
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
                    self.scene.removeItem(item)
                except Exception:
                    pass
        self._uuid_to_item.clear()
        if hard:
            self._remove_all_edge_items_from_scene()

    def _clear_scene_and_graph(self):
        self._reset_interaction_states(remove_hidden_edges=True)
        self._clear_scene_only(hard=True)
        self.graph.clear(silent=True)

    # ---------- View centering ----------

    def content_bounding_rect(self) -> Optional[QRectF]:
        rect: Optional[QRectF] = None
        for item in self._uuid_to_item.values():
            r = item.mapToScene(item.boundingRect()).boundingRect()
            rect = r if rect is None else rect.united(r)
        return rect

    def center_on_content(self, margin: float = 80.0):
        rect = self.content_bounding_rect()
        if rect and rect.isValid():
            padded = rect.adjusted(-margin, -margin, margin, margin)
            self.scene.setSceneRect(self.scene.sceneRect().united(padded))
            self.view.centerOn(rect.center())