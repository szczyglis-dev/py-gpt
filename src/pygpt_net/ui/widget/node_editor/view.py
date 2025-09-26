#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 03:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QPointF, QRectF, QObject, Signal, QSize, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QTransform, QIcon
from PySide6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QPushButton, QHBoxLayout, QLabel

from .config import EditorConfig


# ------------------------ Graphics View / Scene ------------------------

class NodeGraphicsView(QGraphicsView):
    """Zoomable, pannable view with a grid background.

    The view renders a lightweight grid and supports:
    - Ctrl + Mouse Wheel zooming
    - Middle Mouse Button panning
    - Rubber band selection
    - Optional left-button panning only when global grab mode is enabled
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
        self._global_grab_mode = False  # when True, left button pans regardless of items

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw the checker grid in the background."""
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

    def enterEvent(self, e: QEvent):
        """Ensure cursor reflects grab mode when entering the view."""
        if self._global_grab_mode and not self._panning:
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            self.viewport().setCursor(Qt.ArrowCursor)
        super().enterEvent(e)

    def leaveEvent(self, e: QEvent):
        """Restore cursor on leave."""
        self.viewport().setCursor(Qt.ArrowCursor)
        super().leaveEvent(e)

    def keyPressEvent(self, e):
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        super().keyReleaseEvent(e)

    def wheelEvent(self, e):
        """Handle Ctrl + Wheel zoom. Otherwise, default wheel behavior (scroll)."""
        if e.modifiers() & Qt.ControlModifier:
            self._apply_zoom(self._zoom_step if e.angleDelta().y() > 0 else 1.0 / self._zoom_step)
            e.accept()
            return
        super().wheelEvent(e)

    def _begin_pan(self, e):
        """Start panning from current mouse event position."""
        self._panning = True
        self._last_pan_pos = e.position()
        # Use 'grab' during drag
        self.viewport().setCursor(Qt.ClosedHandCursor)
        e.accept()

    def _end_pan(self, e):
        """Stop panning and restore appropriate cursor."""
        self._panning = False
        if self._global_grab_mode:
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            self.viewport().setCursor(Qt.ArrowCursor)
        e.accept()

    def _clicked_on_empty(self, e) -> bool:
        """Return True if the click is on empty scene space (no items)."""
        try:
            item = self.itemAt(int(e.position().x()), int(e.position().y()))
            return item is None
        except Exception:
            return False

    def mousePressEvent(self, e):
        """Panning: MMB always; LMB only in global grab mode. Also clear selection on empty click."""
        if e.button() == Qt.MiddleButton:
            self._begin_pan(e)
            return

        if e.button() == Qt.LeftButton:
            if self._global_grab_mode:
                # Global grab enabled -> pan on LMB anywhere
                self._begin_pan(e)
                return
            else:
                # No global grab: clicking empty clears selection
                if self._clicked_on_empty(e) and self.scene():
                    self.scene().clearSelection()

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
        """Stop panning on Middle or Left Mouse Button release; otherwise defer."""
        if self._panning and e.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._end_pan(e)
            return
        super().mouseReleaseEvent(e)

    def zoom_in(self):
        """Programmatically zoom in by a predefined step."""
        self._apply_zoom(self._zoom_step)

    def zoom_out(self):
        """Programmatically zoom out by a predefined step."""
        self._apply_zoom(1.0 / self._zoom_step)

    def _apply_zoom(self, factor: float):
        """Apply zoom scaling factor within configured bounds."""
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

        self.resetTransform()
        self._zoom = 1.0
        if abs(z - 1.0) > 1e-9:
            self.scale(z, z)
            self._zoom = z

        if keep_center and center_scene is not None:
            self.centerOn(center_scene)

    def get_scroll_values(self) -> Tuple[int, int]:
        h = self.horizontalScrollBar().value() if self.horizontalScrollBar() else 0
        v = self.verticalScrollBar().value() if self.verticalScrollBar() else 0
        return int(h), int(v)

    def set_scroll_values(self, h: int, v: int):
        if self.horizontalScrollBar():
            self.horizontalScrollBar().setValue(int(h))
        if self.verticalScrollBar():
            self.verticalScrollBar().setValue(int(v))

    def view_state(self) -> dict:
        h, v = self.get_scroll_values()
        return {"zoom": float(self._zoom), "h": h, "v": v}

    def set_view_state(self, state: dict):
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
                self.set_scroll_values(self.get_scroll_values()[0], int(v))
        except Exception:
            pass

    def set_global_grab_mode(self, enabled: bool):
        """Enable/disable global grab mode (left click pans anywhere)."""
        self._global_grab_mode = bool(enabled)
        if self._global_grab_mode:
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            if not self._panning:
                self.viewport().setCursor(Qt.ArrowCursor)


class NodeViewOverlayControls(QWidget):
    """Small overlay with three buttons (Grab toggle, Zoom Out, Zoom In) anchored top-right."""

    grabToggled = Signal(bool)
    zoomInClicked = Signal()
    zoomOutClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("NodeViewOverlayControls")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        cfg = self._cfg()

        # Grab (toggle)
        self.btnGrab = QPushButton(self)
        self.btnGrab.setCheckable(True)
        self.btnGrab.setToolTip(cfg.overlay_grab_tooltip())
        self.btnGrab.setIcon(QIcon(":/icons/drag.svg"))
        self.btnGrab.setIconSize(QSize(20, 20))
        self.btnGrab.setMinimumSize(25, 25)

        # Zoom Out
        self.btnZoomOut = QPushButton(self)
        self.btnZoomOut.setToolTip(cfg.overlay_zoom_out_tooltip())
        self.btnZoomOut.setIcon(QIcon(":/icons/zoom_out.svg"))
        self.btnZoomOut.setIconSize(QSize(20, 20))
        self.btnZoomOut.setMinimumSize(25, 25)

        # Zoom In
        self.btnZoomIn = QPushButton(self)
        self.btnZoomIn.setToolTip(cfg.overlay_zoom_in_tooltip())
        self.btnZoomIn.setIcon(QIcon(":/icons/zoom_in.svg"))
        self.btnZoomIn.setIconSize(QSize(20, 20))
        self.btnZoomIn.setMinimumSize(25, 25)

        layout.addWidget(self.btnGrab)
        layout.addWidget(self.btnZoomIn)        
        layout.addWidget(self.btnZoomOut)

        self.btnGrab.toggled.connect(self.grabToggled.emit)
        self.btnZoomIn.clicked.connect(self.zoomInClicked.emit)
        self.btnZoomOut.clicked.connect(self.zoomOutClicked.emit)

        self.show()

    def _cfg(self) -> EditorConfig:
        p = self.parent()
        c = getattr(p, "config", None) if p is not None else None
        return c if isinstance(c, EditorConfig) else EditorConfig()


class NodeViewStatusLabel(QWidget):
    """Fixed status overlay pinned to bottom-left that shows node type counts."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("NodeViewStatusLabel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._lbl = QLabel(self)
        cfg = self._cfg()
        self._lbl.setText(cfg.status_no_nodes())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)  # some padding around the text
        layout.setSpacing(0)
        layout.addWidget(self._lbl)

        self.adjustSize()
        self.show()

    def _cfg(self) -> EditorConfig:
        p = self.parent()
        c = getattr(p, "config", None) if p is not None else None
        return c if isinstance(c, EditorConfig) else EditorConfig()

    def set_text(self, text: str):
        self._lbl.setText(text)
        # Safe: adjustSize() uses sizeHint(), which no longer calls adjustSize()
        self.adjustSize()

    def sizeHint(self):
        """Return hint based on layout/label without calling adjustSize()."""
        if self.layout() is not None:
            return self.layout().sizeHint()
        return self._lbl.sizeHint()


class NodeGraphicsScene(QGraphicsScene):
    """Graphics scene extended with custom context menu emission."""
    sceneContextRequested = Signal(QPointF)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the scene and set a very large scene rect."""
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def contextMenuEvent(self, event):
        """Emit a scene-level context menu request when clicking empty space."""
        transform = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(event.scenePos(), transform)
        if item is None:
            # Respect external edit permission if available on parent editor
            editor = self.parent()
            allowed = True
            try:
                if hasattr(editor, "editing_allowed") and callable(editor.editing_allowed):
                    allowed = bool(editor.editing_allowed())
            except Exception:
                allowed = False
            if allowed:
                self.sceneContextRequested.emit(event.scenePos())
            event.accept()
            return
        super().contextMenuEvent(event)