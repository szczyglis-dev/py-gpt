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
from typing import Optional, List, Tuple, Dict

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPainter, QPainterPath, QPen, QPainterPathStroker, QFont
from PySide6.QtWidgets import (
    QWidget, QGraphicsItem, QGraphicsPathItem, QGraphicsObject, QStyleOptionGraphicsItem, QMenu, QGraphicsSimpleTextItem
)

from .utils import _qt_is_valid


# ------------------------ Items: Port, Edge, Node ------------------------

class PortItem(QGraphicsObject):
    """Circular port that can initiate and accept connections.

    A port is associated with a node property (prop_id) and has a side:
    - 'input'  for inbound connections
    - 'output' for outbound connections

    The item also renders a small capacity label (how many connections are allowed),
    based on the live node type specification from the registry.
    """
    radius = 6.0
    portClicked = Signal(object)   # self
    side: str  # "input" or "output"

    def __init__(self, node_item: "NodeItem", prop_id: str, side: str):
        """Create a new port item.

        Args:
            node_item: Parent NodeItem to which this port belongs.
            prop_id: Property identifier this port represents.
            side: 'input' or 'output'.
        """
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

        # Small label for capacity only (IN/OUT removed from UI)
        self._label_io = QGraphicsSimpleTextItem(self)     # kept for compatibility; hidden
        self._label_cap = QGraphicsSimpleTextItem(self)

        # Fonts for capacity label
        self._font_small = QFont()
        self._font_small.setPixelSize(9)
        self._font_cap_num = QFont()
        self._font_cap_num.setPixelSize(9)
        self._font_cap_inf = QFont()
        self._font_cap_inf.setPixelSize(14)  # slightly bigger infinity sign for readability

        self._label_io.setFont(self._font_small)
        self._label_cap.setFont(self._font_cap_num)

        self._update_label_texts()
        self._update_label_colors()
        self._update_label_positions()
        self._update_tooltip()  # initial tooltip

    def _allowed_capacity(self) -> Optional[int]:
        """Return allowed connection count for this port from live registry/spec."""
        return self.node_item.allowed_capacity_for_pid(self.prop_id, self.side)

    def _update_label_texts(self):
        """Update label texts to reflect current capacity for this port."""
        # Hide IN/OUT label completely
        self._label_io.setText("")
        self._label_io.setVisible(False)

        # Capacity: show max allowed for this port side from live spec
        cap_val = self._allowed_capacity()
        text = ""
        if isinstance(cap_val, int) and cap_val != 0:
            if cap_val < 0:
                text = "\u221E"
            else:
                text = str(cap_val)
        self._label_cap.setText(text)
        # Adjust capacity font: make infinity larger, keep numbers as-is
        if text == "\u221E":
            self._label_cap.setFont(self._font_cap_inf)
        else:
            self._label_cap.setFont(self._font_cap_num)

    def _update_label_colors(self):
        """Apply theme colors to the labels."""
        editor = self.node_item.editor
        self._label_io.setBrush(QBrush(editor._port_label_color))
        self._label_cap.setBrush(QBrush(editor._port_capacity_color))

    def _update_label_positions(self):
        """Position capacity label around the port, respecting the port side."""
        r = self.radius
        cap_rect = self._label_cap.boundingRect()
        gap = 3.0

        # Move capacity label up by additional ~3px (total ~7px up from original baseline)
        dy_cap = -6.0

        if self.side == "input":
            if self._label_cap.text():
                cap_x = -r - gap - cap_rect.width()
                self._label_cap.setPos(cap_x, -cap_rect.height() / 2.0 + dy_cap)
            else:
                self._label_cap.setPos(-r - gap, -cap_rect.height() / 2.0 + dy_cap)
        else:
            if self._label_cap.text():
                cap_x = r + gap
                self._label_cap.setPos(cap_x, -cap_rect.height() / 2.0 + dy_cap)
            else:
                self._label_cap.setPos(r + gap, -cap_rect.height() / 2.0 + dy_cap)

    def _update_tooltip(self):
        """Build and apply a helpful tooltip for this port.

        Shows node name, port side/id, and allowed connections, with interaction hints.
        """
        node_name = ""
        try:
            node_name = self.node_item.node.name
        except Exception:
            pass
        cap_val = self._allowed_capacity()
        cfg = self.node_item.editor.config
        if isinstance(cap_val, int):
            if cap_val < 0:
                cap_str = cfg.cap_unlimited()
            else:
                cap_str = str(cap_val)
        else:
            cap_str = cfg.cap_na()
        side_label = cfg.side_label(self.side).upper()
        tip = cfg.port_tooltip(node_name, side_label, self.prop_id, cap_str)
        self.setToolTip(tip)
        try:
            self._label_cap.setToolTip(tip)
        except Exception:
            pass

    def notify_theme_changed(self):
        """Refresh colors when global theme changes."""
        self._update_label_colors()
        self.update()

    def boundingRect(self) -> QRectF:
        """Compute a bounding rect large enough for the port and its label."""
        r = self.radius
        cap_rect = self._label_cap.boundingRect()
        gap = 3.0
        cap_text = self._label_cap.text()

        # Allocate space only for the capacity label (IN/OUT removed)
        left_extra = 6.0
        right_extra = 6.0
        if self.side == "input" and cap_text:
            left_extra = gap + cap_rect.width() + 4.0
        if self.side == "output" and cap_text:
            right_extra = gap + cap_rect.width() + 4.0

        # Add a bit more vertical padding to fully cover the label lifted upwards
        h = max(2 * r, cap_rect.height()) + 12.0
        w = 2 * r + left_extra + right_extra
        return QRectF(-r - left_extra, -h / 2.0, w, h)

    def shape(self) -> QPainterPath:
        """Use a larger 'pick' radius for easier mouse interaction."""
        pick_r = float(getattr(self.node_item.editor, "_port_pick_radius", 10.0)) or 10.0
        p = QPainterPath()
        p.addEllipse(QRectF(-pick_r, -pick_r, 2 * pick_r, 2 * pick_r))
        return p

    def paint(self, p: QPainter, opt: QStyleOptionGraphicsItem, widget=None):
        """Render the port as a filled circle with an optional highlight ring."""
        editor = self.node_item.editor
        base = editor._port_input_color if self.side == "input" else editor._port_output_color
        color = editor._port_connected_color if self._connected_count > 0 else base
        if self._hover:
            color = color.lighter(130)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius))
        if self._can_accept:
            ring = QPen(editor._port_accept_color, 3.0)
            ring.setCosmetic(True)
            p.setPen(ring)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius))

    def hoverEnterEvent(self, e):
        """Enable hover flag and repaint."""
        self._hover = True
        self.update()
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        """Disable hover flag and repaint."""
        self._hover = False
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        """Emit portClicked on left click to begin a connection or rewire."""
        if e.button() == Qt.LeftButton:
            try:
                # Bring parent node to front when clicking the port
                self.node_item.editor.raise_node_to_top(self.node_item)
            except Exception:
                pass
            self.node_item.editor._dbg(f"Port clicked: side={self.side}, node={self.node_item.node.name}({self.node_item.node.uuid}), prop={self.prop_id}, connected_count={self._connected_count}")
            self.portClicked.emit(self)
            e.accept()
            return
        super().mousePressEvent(e)

    def increment_connections(self, delta: int):
        """Increment or decrement the connected edges counter and repaint.

        Args:
            delta: Positive to increase, negative to decrease. Result is clamped to >= 0.
        """
        self._connected_count = max(0, self._connected_count + delta)
        self.update()

    def set_accept_highlight(self, enabled: bool):
        """Toggle a visible 'can accept connection' ring."""
        if self._can_accept != enabled:
            self._can_accept = enabled
            self.update()

    def update_labels(self):
        """Rebuild label text/position and tooltip (e.g., after spec/theme change)."""
        self._update_label_texts()
        self._update_label_positions()
        self._update_tooltip()
        self.update()


class EdgeItem(QGraphicsPathItem):
    """Cubic bezier edge connecting two PortItem endpoints.

    The item can be temporary (during interaction) or persistent (synced with the model).
    It supports selection, hover highlight and a context menu for deletion.
    """
    def __init__(self, src_port: PortItem, dst_port: PortItem, temporary: bool = False):
        """Initialize an edge between src_port and dst_port.

        Args:
            src_port: Output side port.
            dst_port: Input side port (or same as src during interactive drag).
            temporary: When True, draws with dashed pen and does not expose context actions.
        """
        super().__init__()
        self.src_port = src_port
        self.dst_port = dst_port
        self.temporary = temporary
        self.setZValue(1)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self._editor = self.src_port.node_item.editor
        self._hover = False
        self._drag_primed = False
        self._drag_start_scene = QPointF()
        self._update_pen()

    def set_hovered(self, hovered: bool):
        """Set hover state and refresh pen color."""
        if self._hover != hovered:
            self._hover = hovered
            self._update_pen()

    def _update_pen(self):
        """Update the pen based on hover/selection/temporary state."""
        color = self._editor._edge_selected_color if (self._hover or self.isSelected()) else self._editor._edge_color
        pen = QPen(color)
        pen.setWidthF(2.0 if not self.temporary else 1.5)
        pen.setStyle(Qt.SolidLine if not self.temporary else Qt.DashLine)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.update()

    def itemChange(self, change, value):
        """Refresh pen when selection state changes."""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._update_pen()
        return super().itemChange(change, value)

    def shape(self) -> QPainterPath:
        """Return an inflated path for comfortable picking/selection."""
        stroker = QPainterPathStroker()
        width = float(getattr(self._editor, "_edge_pick_width", 12.0) or 12.0)
        stroker.setWidth(width)
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(self.path())

    def update_path(self, end_pos: Optional[QPointF] = None):
        """Recompute the cubic path between endpoints.

        Args:
            end_pos: Optional scene position for the free endpoint while dragging.
                     When None, uses dst_port scenePos().

        Notes:
            Control points are placed horizontally at 50% of the delta X for a classic bezier look.
        """
        try:
            sp = getattr(self, "src_port", None)
            dp = getattr(self, "dst_port", None)
            if not _qt_is_valid(sp):
                return
            p0 = sp.scenePos()
            if end_pos is not None:
                p1 = end_pos
            else:
                if not _qt_is_valid(dp):
                    return
                p1 = dp.scenePos()

            dx = abs(p1.x() - p0.x())
            c1 = QPointF(p0.x() + dx * 0.5, p0.y())
            c2 = QPointF(p1.x() - dx * 0.5, p1.y())
            p = QPainterPath()
            p.moveTo(p0)
            p.cubicTo(c1, c2, p1)
            self.setPath(p)
        except Exception:
            # Fail-safe during GC/teardown
            return

    def contextMenuEvent(self, event):
        """Show a context menu to delete this connection (only for persistent edges)."""
        if self.temporary:
            return
        self._editor._dbg(f"Edge context menu on edge id={id(self)}")
        menu = QMenu(self._editor.window())
        ss = self._editor.window().styleSheet()
        if ss:
            menu.setStyleSheet(ss)
        act_del = QAction(self._editor.config.edge_context_delete(), menu)
        menu.addAction(act_del)
        chosen = menu.exec(event.screenPos())
        if chosen == act_del:
            self._editor._dbg(f"Context DELETE on edge id={id(self)} (undoable)")
            self._editor._delete_edge_undoable(self)

    def mousePressEvent(self, e):
        """Prime dragging on left-click, enabling rewire from edge."""
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
        """When drag threshold is exceeded, start interactive rewire from edge."""
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
        """Reset the primed state on release."""
        self._drag_primed = False
        super().mouseReleaseEvent(e)


class NodeOverlayItem(QGraphicsItem):
    """Lightweight overlay drawn above the proxy widget to add subtle guides.

    The overlay inspects the positions of property editors inside NodeContentWidget and
    draws separators between rows to improve readability.
    """
    def __init__(self, node_item: "NodeItem"):
        """Create an overlay attached to the given NodeItem."""
        super().__init__(node_item)
        self.node_item = node_item
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(False)
        self.setZValue(2.1)
        # Track which property row is hovered to paint a subtle background
        self._hover_pid: Optional[str] = None

    def boundingRect(self) -> QRectF:
        """Compute the overlay rect (content area below the title)."""
        ni = self.node_item
        hit = ni._effective_hit_margin()
        return QRectF(0.0, float(ni._title_height),
                      max(0.0, ni.size().width() - hit),
                      max(0.0, ni.size().height() - ni._title_height - hit))

    def set_hover_pid(self, pid: Optional[str]):
        """Set hovered property id to be highlighted."""
        if self._hover_pid != pid:
            self._hover_pid = pid
            self.update()

    def paint(self, p: QPainter, opt: QStyleOptionGraphicsItem, widget=None):
        """Draw full-width separators and a hover background that snaps to separators (no vertical gaps)."""
        ni = self.node_item
        if not _qt_is_valid(ni):
            return
        p.setRenderHint(QPainter.Antialiasing, True)

        base = QColor(ni.editor._node_border_color)
        br = self.boundingRect()
        left = br.left()     # full width
        right = br.right()   # full width

        try:
            # Collect editor widgets -> rows and keep property order
            editors: List[Tuple[str, QWidget]] = []
            for pid in ni.node.properties.keys():
                w = ni._content._editors.get(pid)
                if isinstance(w, QWidget) and _qt_is_valid(w):
                    editors.append((pid, w))
            if not editors:
                return

            proxy_off = ni._proxy.pos()
            rows: List[Tuple[str, float, float]] = []
            for pid, w in editors:
                geo = w.geometry()
                top = float(proxy_off.y()) + float(geo.y())
                bottom = top + float(geo.height())
                rows.append((pid, top, bottom))

            # Compute separator lines at mid-gap between consecutive rows (clamped to overlay bounds)
            seps: List[float] = []
            for i in range(len(rows) - 1):
                _, _, bottom_a = rows[i]
                _, top_b, _ = rows[i + 1]
                y = (bottom_a + top_b) * 0.5
                if br.top() <= y <= br.bottom():
                    seps.append(y)

            # Build vertical zones per row: from previous separator to next separator (or overlay edges)
            zones: Dict[str, Tuple[float, float]] = {}
            for i, (pid, _top, _bottom) in enumerate(rows):
                z_top = br.top() if i == 0 else (seps[i - 1] if (i - 1) < len(seps) else br.top())
                z_bot = br.bottom() if i == len(rows) - 1 else (seps[i] if i < len(seps) else br.bottom())
                # Ensure within overlay bounds
                z_top = max(br.top(), min(z_top, br.bottom()))
                z_bot = max(br.top(), min(z_bot, br.bottom()))
                if z_bot > z_top:
                    zones[pid] = (z_top, z_bot)

            # 1) Hover background: full width, vertically up to separators (no gap)
            if self._hover_pid and self._hover_pid in zones:
                y1, y2 = zones[self._hover_pid]
                hl = QColor(base.lighter(170))
                hl.setAlpha(25)  # subtle
                p.fillRect(QRectF(left, y1, right - left, y2 - y1), hl)

            # 2) Full-width separators
            sep = QColor(base.lighter(160))
            sep.setAlpha(130)
            pen_sep = QPen(sep, 1.25, Qt.SolidLine)
            pen_sep.setCosmetic(True)
            p.setPen(pen_sep)
            for y in seps:
                if br.top() + 0.5 <= y <= br.bottom() - 0.5:
                    p.drawLine(QPointF(left, y), QPointF(right, y))
        except Exception:
            pass