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
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF, QObject, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QTransform
from PySide6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene


# ------------------------ Graphics View / Scene ------------------------

class NodeGraphicsView(QGraphicsView):
    """Zoomable, pannable view with a grid background.

    The view renders a lightweight grid and supports:
    - Ctrl + Mouse Wheel zooming
    - Middle Mouse Button panning
    - Rubber band selection

    Notes:
        - Space-panning is intentionally disabled to not conflict with typing in editors.
        - All keyboard shortcuts (e.g., Delete) are handled at the NodeEditor level.

    Args:
        scene: Shared QGraphicsScene instance for the editor.
        parent: Optional parent widget.
    """
    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None):
        super().__init__(scene, parent)
        self.setRenderHints(self.renderHints() |
                            QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        a = QGraphicsView.AnchorViewCenter
        self.setResizeAnchor(a)
        self.setFocusPolicy(Qt.StrongFocus)

        self._zoom = 1.0
        self._zoom_step = 1.15
        self._min_zoom = 0.2
        self._max_zoom = 3.0

        self._panning = False
        self._last_pan_pos = None

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw the checker grid in the background.

        The grid spacing is fixed (20 px). Colors are read from the owning NodeEditor
        instance if available, which allows dynamic theming.

        Args:
            painter: Active QPainter provided by Qt.
            rect: The exposed background rect to be filled.
        """
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
        """Pass-through: the view does not handle special keys.

        ESC and other keys are intentionally left for the host application/editor.
        """
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        """Pass-through for key release."""
        super().keyReleaseEvent(e)

    def wheelEvent(self, e):
        """Handle Ctrl + Wheel zoom. Otherwise, default wheel behavior (scroll)."""
        if e.modifiers() & Qt.ControlModifier:
            self._apply_zoom(self._zoom_step if e.angleDelta().y() > 0 else 1.0 / self._zoom_step)
            e.accept()
            return
        super().wheelEvent(e)

    def mousePressEvent(self, e):
        """Start panning with Middle Mouse Button; otherwise defer to base implementation."""
        if e.button() == Qt.MiddleButton:
            self._panning = True
            self._last_pan_pos = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """While panning, translate scrollbars. Otherwise defer."""
        if self._panning and self._last_pan_pos is not None:
            delta = e.position() - self._last_pan_pos
            self._last_pan_pos = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Stop panning on Middle Mouse Button release; otherwise defer."""
        if self._panning and e.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def zoom_in(self):
        """Programmatically zoom in by a predefined step."""
        self._apply_zoom(self._zoom_step)

    def zoom_out(self):
        """Programmatically zoom out by a predefined step."""
        self._apply_zoom(1.0 / self._zoom_step)

    def _apply_zoom(self, factor: float):
        """Apply zoom scaling factor within configured bounds.

        Args:
            factor: Multiplicative factor to apply to the current zoom.

        Notes:
            The method clamps the result to [_min_zoom, _max_zoom] to prevent
            excessive zooming.
        """
        new_zoom = self._zoom * factor
        if not (self._min_zoom <= new_zoom <= self._max_zoom):
            return
        self._zoom = new_zoom
        self.scale(factor, factor)

    def zoom_value(self) -> float:
        """Return the current zoom factor."""
        return float(self._zoom)

    def set_zoom_value(self, zoom: float, keep_center: bool = False):
        """Set an absolute zoom factor and optionally keep the current viewport center."""
        if zoom is None:
            return
        z = max(self._min_zoom, min(self._max_zoom, float(zoom)))
        center_scene = None
        if keep_center and self.viewport() is not None and self.viewport().rect().isValid():
            center_scene = self.mapToScene(self.viewport().rect().center())

        # Reset and apply new transform to avoid cumulative floating errors
        self.resetTransform()
        self._zoom = 1.0
        if abs(z - 1.0) > 1e-9:
            self.scale(z, z)
            self._zoom = z

        if keep_center and center_scene is not None:
            self.centerOn(center_scene)

    def get_scroll_values(self) -> Tuple[int, int]:
        """Return (horizontal, vertical) scrollbar values."""
        h = self.horizontalScrollBar().value() if self.horizontalScrollBar() else 0
        v = self.verticalScrollBar().value() if self.verticalScrollBar() else 0
        return int(h), int(v)

    def set_scroll_values(self, h: int, v: int):
        """Set horizontal and vertical scrollbar values."""
        if self.horizontalScrollBar():
            self.horizontalScrollBar().setValue(int(h))
        if self.verticalScrollBar():
            self.verticalScrollBar().setValue(int(v))

    def view_state(self) -> dict:
        """Return a serializable view state: zoom and scrollbars."""
        h, v = self.get_scroll_values()
        return {"zoom": float(self._zoom), "h": h, "v": v}

    def set_view_state(self, state: dict):
        """Apply a view state previously produced by view_state()."""
        if not isinstance(state, dict):
            return
        z = state.get("zoom") or state.get("scale")
        if z is not None:
            try:
                self.set_zoom_value(float(z), keep_center=False)
            except Exception:
                pass
        h = state.get("h") or state.get("hScroll") or state.get("x")
        v = state.get("v") or state.get("vScroll") or state.get("y")
        try:
            if h is not None:
                self.set_scroll_values(int(h), int(v if v is not None else 0))
            elif v is not None:
                # set vertical if only v present
                self.set_scroll_values(self.get_scroll_values()[0], int(v))
        except Exception:
            pass


class NodeGraphicsScene(QGraphicsScene):
    """Graphics scene extended with custom context menu emission."""
    sceneContextRequested = Signal(QPointF)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the scene and set a very large scene rect.

        Using a large default rect avoids sudden scene rect changes while panning/zooming.
        """
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def contextMenuEvent(self, event):
        """Emit a scene-level context menu request when clicking empty space.

        If the click is not on any item, the signal sceneContextRequested is emitted with
        the scene position. Otherwise, default handling is used (propagating to items).
        """
        transform = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(event.scenePos(), transform)
        if item is None:
            self.sceneContextRequested.emit(event.scenePos())
            event.accept()
            return
        super().contextMenuEvent(event)

