#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.28 14:30:00                  #
# ================================================== #

import datetime
import os
import bisect
import math
from collections import deque

from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QSize, QSaveFile, QIODevice, QTimer, Signal
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon, QColor, QCursor
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox, QApplication, QAbstractScrollArea

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class PainterWidget(QWidget):
    # Emitted whenever zoom changes; payload is zoom factor (e.g. 1.0 for 100%)
    zoomChanged = Signal(float)

    def __init__(self, window=None):
        super().__init__(window)
        self.window = window

        # Logical canvas size (in pixels). Rendering buffers follow this, never the display size.
        w0 = max(1, self.width())
        h0 = max(1, self.height())
        self._canvasSize = QSize(w0, h0)

        # Zoom state (pure view transform; does not affect canvas resolution)
        self.zoom = 1.0
        self._minZoom = 0.10    # 10%
        self._maxZoom = 10.0    # 1000%
        self._zoomSteps = [0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 5.00, 10.00]
        self._zoomResizeInProgress = False  # guard used during display-size updates caused by zoom

        # Guard to mark an explicit logical canvas resize (controller-driven)
        self._canvasResizeInProgress = False

        # Final composited image (canvas-sized). Kept for API compatibility.
        self.image = QImage(self._canvasSize, QImage.Format_RGB32)

        # Layered model:
        # - sourceImageOriginal: original background image (full quality, not canvas-sized).
        # - baseCanvas: canvas-sized background with the source scaled to fit (letterboxed).
        # - drawingLayer: canvas-sized transparent layer for strokes.
        self.sourceImageOriginal = None
        self.baseCanvas = None
        self.baseTargetRect = QRect()
        self.drawingLayer = None

        # Drawing state
        self.drawing = False
        self._mouseDown = False
        self.brushSize = 3
        self.brushColor = Qt.black
        self._mode = "brush"  # "brush" or "erase"
        self.lastPointCanvas = QPoint()
        self._pen = QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        # Crop tool state (selection kept in canvas coordinates)
        self.cropping = False
        self._selecting = False
        self._selectionStart = QPoint()
        self._selectionRect = QRect()

        # Undo/redo: store full layered state to support non-destructive operations
        self.undoLimit = 10
        self.undoStack = deque(maxlen=self.undoLimit)
        self.redoStack = deque()

        self.originalImage = None  # kept for API compatibility; reflects current composited image
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.installEventFilter(self)

        self.tab = None

        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_StaticContents, True)

        # Internal flags
        self._pendingResizeApply = None  # payload used after crop to apply exact pixels on resize
        self._ignoreResizeOnce = False   # guard to prevent recursive work in resize path

        # Auto-scroll while cropping (scroll area integration)
        self._scrollArea = None
        self._scrollViewport = None
        self._autoScrollTimer = QTimer(self)
        self._autoScrollTimer.setInterval(16)  # ~60 FPS, low overhead
        self._autoScrollTimer.timeout.connect(self._autoscroll_tick)
        self._autoScrollMargin = 36            # px from viewport edge to trigger autoscroll
        self._autoScrollMinSpeed = 2           # px per tick (min)
        self._autoScrollMaxSpeed = 18          # px per tick (max)

        # Pan (middle mouse) state
        self._panning = False
        self._panLastGlobalPos = QPoint()
        self._cursorBeforePan = None  # store/restore cursor shape while panning

        # Actions
        self._act_undo = QAction(QIcon(":/icons/undo.svg"), trans('action.undo'), self)
        self._act_undo.triggered.connect(self.undo)

        self._act_redo = QAction(QIcon(":/icons/redo.svg"), trans('action.redo'), self)
        self._act_redo.triggered.connect(self.redo)

        self._act_copy = QAction(QIcon(":/icons/copy.svg"), trans('action.copy'), self)
        self._act_copy.triggered.connect(self.handle_copy)

        self._act_paste = QAction(QIcon(":/icons/paste.svg"), trans('action.paste'), self)
        self._act_paste.triggered.connect(self.handle_paste)

        self._act_open = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open'), self)
        self._act_open.triggered.connect(self.action_open)

        self._act_capture = QAction(QIcon(":/icons/fullscreen.svg"), trans('painter.btn.capture'), self)
        self._act_capture.triggered.connect(self.action_capture)

        self._act_save = QAction(QIcon(":/icons/save.svg"), trans('img.action.save'), self)
        self._act_save.triggered.connect(self.action_save)

        self._act_clear = QAction(QIcon(":/icons/close.svg"), trans('painter.btn.clear'), self)
        self._act_clear.triggered.connect(self.action_clear)

        # Crop action (also add this QAction to your top toolbar if desired)
        self._act_crop = QAction(QIcon(":/icons/crop.svg"), trans('painter.btn.crop') if trans('painter.btn.crop') else "Crop", self)
        self._act_crop.triggered.connect(self.start_crop)

        # Fit action (trims letterbox and resizes canvas to the scaled image area)
        self._act_fit = QAction(QIcon(":/icons/fit.svg"), trans('painter.btn.fit') if trans('painter.btn.fit') else "Fit", self)
        self._act_fit.triggered.connect(self.action_fit)

        # Context menu
        self._ctx_menu = QMenu(self)
        self._ctx_menu.addAction(self._act_undo)
        self._ctx_menu.addAction(self._act_redo)
        self._ctx_menu.addSeparator()
        self._ctx_menu.addAction(self._act_crop)
        self._ctx_menu.addAction(self._act_fit)
        self._ctx_menu.addSeparator()
        self._ctx_menu.addSeparator()
        self._ctx_menu.addAction(self._act_open)
        self._ctx_menu.addAction(self._act_capture)
        self._ctx_menu.addAction(self._act_copy)
        self._ctx_menu.addAction(self._act_paste)
        self._ctx_menu.addAction(self._act_save)
        self._ctx_menu.addAction(self._act_clear)

        # Composite state: mark when self.image is out-of-date relative to layers
        self._compositeDirty = True  # True => recomposition needed before exporting/copying

        # Allocate initial buffers
        self._ensure_layers()
        self._recompose()
        # Keep display size in sync with zoom (initially 1.0 => no change)
        self._update_widget_size_from_zoom()

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    # ---------- Canvas public API (explicit, zoom-independent) ----------

    def set_canvas_size_pixels(self, width: int, height: int):
        """
        Explicitly set logical canvas size in pixels.
        This never depends on view zoom and never uses parent/layout resizes.

        :param width: canvas width in pixels
        :param height: canvas height in pixels
        """
        w = max(1, int(width))
        h = max(1, int(height))

        if self._canvasSize.width() == w and self._canvasSize.height() == h:
            # Keep display size consistent with current zoom
            self._update_widget_size_from_zoom()
            return

        old_canvas = QSize(self._canvasSize)
        self._canvasSize = QSize(w, h)

        self._canvasResizeInProgress = True
        try:
            self._handle_canvas_resized(old_canvas, self._canvasSize)
            # After logical resize, update the displayed size according to zoom
            self._update_widget_size_from_zoom()
        finally:
            self._canvasResizeInProgress = False

    def get_canvas_size(self) -> QSize:
        """
        Return current logical canvas size (pixels).

        :return: QSize of canvas
        """
        return QSize(self._canvasSize)

    # ---------- Zoom public API ----------

    def on_zoom_combo_changed(self, text: str):
        """
        Slot for a zoom ComboBox change. Accepts strings like "100%" or "150 %".

        :param text: Text from the combo box
        """
        val = self._parse_percent(text)
        if val is None:
            return
        # Use viewport center as anchor when changed from combobox
        anchor = self._viewport_center_in_widget_coords()
        self.set_zoom(val / 100.0, anchor_widget_pos=anchor)

    def set_zoom_percent(self, percent: int):
        """
        Set zoom using percent value, e.g. 150 for 150%.

        :param percent: Zoom in percent
        """
        anchor = self._viewport_center_in_widget_coords()
        self.set_zoom(max(1, percent) / 100.0, anchor_widget_pos=anchor)

    def get_zoom_percent(self) -> int:
        """
        Return current zoom as integer percent.

        :return: Zoom in percent (e.g. 150 for 150%)
        """
        return int(round(self.zoom * 100.0))

    def get_zoom_steps_percent(self) -> list[int]:
        """
        Return recommended preset zoom steps in percent for a combo-box.

        :return: List of zoom steps in percent
        """
        return [int(round(z * 100)) for z in self._zoomSteps]

    def set_zoom(self, zoom: float, anchor_widget_pos: QPointF | None = None, emit_signal: bool = True):
        """
        Set zoom to an absolute factor. View-only; does not touch canvas resolution.
        anchor_widget_pos: QPointF in widget coordinates; if None, viewport center is used.

        :param zoom: Zoom factor (e.g. 1.0 for 100%)
        :param anchor_widget_pos: Anchor point in widget coordinates to keep stable during zoom
        :param emit_signal: Whether to emit zoomChanged signal and sync combobox
        """
        new_zoom = max(self._minZoom, min(self._maxZoom, float(zoom)))
        if abs(new_zoom - self.zoom) < 1e-6:
            return

        old_zoom = self.zoom
        self.zoom = new_zoom

        # Sync UI (combobox) and emit signal
        if emit_signal:
            self._emit_zoom_changed()

        # Update display size and scroll to keep anchor stable
        if anchor_widget_pos is None:
            anchor_widget_pos = self._viewport_center_in_widget_coords()
        self._update_widget_size_from_zoom()
        self._adjust_scroll_to_anchor(anchor_widget_pos, old_zoom, self.zoom)

        self.update()

    def zoom_in_step(self):
        """Increase zoom to next preset step."""
        idx = self._nearest_zoom_step_index(self.zoom)
        if idx < len(self._zoomSteps) - 1:
            self.set_zoom(self._zoomSteps[idx + 1], anchor_widget_pos=self._cursor_pos_in_widget())

    def zoom_out_step(self):
        """Decrease zoom to previous preset step."""
        idx = self._nearest_zoom_step_index(self.zoom)
        if idx > 0:
            self.set_zoom(self._zoomSteps[idx - 1], anchor_widget_pos=self._cursor_pos_in_widget())

    # ---------- Internal zoom helpers ----------

    def _emit_zoom_changed(self):
        """Emit signal and try to sync external combobox via controller if available."""
        self.zoomChanged.emit(self.zoom)
        try:
            if self.window and hasattr(self.window, "controller"):
                common = getattr(self.window.controller.painter, "common", None)
                if common is not None:
                    # Preferred method name
                    if hasattr(common, "sync_zoom_combo_from_widget"):
                        common.sync_zoom_combo_from_widget(self.get_zoom_percent())
                    # Fallback method names that may exist in some UIs
                    elif hasattr(common, "set_zoom_percent"):
                        common.set_zoom_percent(self.get_zoom_percent())
                    elif hasattr(common, "set_zoom_value"):
                        common.set_zoom_value(self.get_zoom_percent())
        except Exception:
            pass

    def _nearest_zoom_step_index(self, z: float) -> int:
        """
        Find index of the nearest step to z in _zoomSteps.

        :param z: Zoom factor
        :return: Index of the nearest zoom step
        """
        steps = self._zoomSteps
        pos = bisect.bisect_left(steps, z)
        if pos == 0:
            return 0
        if pos >= len(steps):
            return len(steps) - 1
        before = steps[pos - 1]
        after = steps[pos]
        return pos if abs(after - z) < abs(z - before) else pos - 1

    def _cursor_pos_in_widget(self) -> QPointF:
        """
        Return current cursor position in widget coordinates.

        :return: QPointF in widget coordinates
        """
        return QPointF(self.mapFromGlobal(QCursor.pos()))

    def _viewport_center_in_widget_coords(self) -> QPointF:
        """
        Return viewport center mapped to widget coordinates; falls back to widget center.

        :return: QPointF in widget coordinates
        """
        self._find_scroll_area()
        if self._scrollViewport is not None:
            vp = self._scrollViewport
            center_vp = QPointF(vp.width() / 2.0, vp.height() / 2.0)
            return QPointF(self.mapFrom(vp, center_vp.toPoint()))
        return QPointF(self.width() / 2.0, self.height() / 2.0)

    def _adjust_scroll_to_anchor(self, anchor_widget_pos: QPointF, old_zoom: float, new_zoom: float):
        """
        Adjust scrollbars to keep the anchor point stable in viewport during zoom.

        :param anchor_widget_pos: Anchor point in widget coordinates
        :param old_zoom: Previous zoom factor
        :param new_zoom: New zoom factor
        """
        self._find_scroll_area()
        if self._scrollArea is None or self._scrollViewport is None:
            return
        hbar = self._scrollArea.horizontalScrollBar()
        vbar = self._scrollArea.verticalScrollBar()
        if hbar is None and vbar is None:
            return
        scale = new_zoom / max(1e-6, old_zoom)
        dx = anchor_widget_pos.x() * (scale - 1.0)
        dy = anchor_widget_pos.y() * (scale - 1.0)
        if hbar is not None:
            hbar.setValue(int(round(hbar.value() + dx)))
        if vbar is not None:
            vbar.setValue(int(round(vbar.value() + dy)))

    def _update_widget_size_from_zoom(self):
        """Resize display widget to reflect current zoom; leaves canvas buffers untouched."""
        disp_w = max(1, int(round(self._canvasSize.width() * self.zoom)))
        disp_h = max(1, int(round(self._canvasSize.height() * self.zoom)))
        new_disp = QSize(disp_w, disp_h)
        if self.size() == new_disp:
            return
        self._zoomResizeInProgress = True
        try:
            # setFixedSize is preferred for content widgets inside scroll areas
            self.setFixedSize(new_disp)
        finally:
            self._zoomResizeInProgress = False

    def _to_canvas_point(self, pt) -> QPoint:
        """
        Map a widget point (QPoint or QPointF) to canvas coordinates.

        :param pt: QPoint or QPointF in widget coordinates
        :return: QPoint in canvas coordinates
        """
        if isinstance(pt, QPointF):
            x = int(round(pt.x() / self.zoom))
            y = int(round(pt.y() / self.zoom))
        else:
            x = int(round(pt.x() / self.zoom))
            y = int(round(pt.y() / self.zoom))
        x = max(0, min(self._canvasSize.width() - 1, x))
        y = max(0, min(self._canvasSize.height() - 1, y))
        return QPoint(x, y)

    def _from_canvas_rect(self, rc: QRect) -> QRect:
        """
        Map a canvas rect to widget/display coordinates.

        :param rc: QRect in canvas coordinates
        :return: QRect in widget coordinates
        """
        x = int(round(rc.x() * self.zoom))
        y = int(round(rc.y() * self.zoom))
        w = int(round(rc.width() * self.zoom))
        h = int(round(rc.height() * self.zoom))
        return QRect(x, y, w, h)

    def _widget_rect_to_canvas_rect(self, rc: QRect) -> QRect:
        """
        Map a widget rect (in display pixels) to a canvas rect (in canvas pixels).
        Uses floor/ceil to ensure coverage and clamps to canvas bounds.
        """
        if rc.isNull() or rc.width() <= 0 or rc.height() <= 0:
            return QRect()
        inv = 1.0 / max(1e-6, self.zoom)
        x1 = int(math.floor(rc.x() * inv))
        y1 = int(math.floor(rc.y() * inv))
        x2 = int(math.ceil((rc.x() + rc.width()) * inv))
        y2 = int(math.ceil((rc.y() + rc.height()) * inv))
        x1 = max(0, min(self._canvasSize.width(), x1))
        y1 = max(0, min(self._canvasSize.height(), y1))
        x2 = max(0, min(self._canvasSize.width(), x2))
        y2 = max(0, min(self._canvasSize.height(), y2))
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        return QRect(x1, y1, w, h)

    def _parse_percent(self, text: str) -> int | None:
        """
        Parse '150%' -> 150.

        Returns None if parsing fails.

        :param text: Text to parse
        :return: Integer percent or None
        """
        if not text:
            return None
        try:
            s = text.strip().replace('%', '').strip()
            s = s.replace(',', '.')
            valf = float(s)
            return int(round(valf))
        except Exception:
            return None

    # ---------- Layer & composition helpers ----------

    def _mark_composite_dirty(self):
        """Mark the composited image cache as dirty."""
        self._compositeDirty = True

    def _ensure_composited_image(self):
        """
        Ensure that self.image reflects current baseCanvas + drawingLayer.
        This is used for exporting/copying, not for on-screen painting.
        """
        if self._compositeDirty:
            self._recompose()
            self._compositeDirty = False

    def _ensure_layers(self):
        """Ensure baseCanvas, drawingLayer, and image are allocated to current canvas size."""
        sz = self._canvasSize
        if sz.width() <= 0 or sz.height() <= 0:
            return

        if self.baseCanvas is None or self.baseCanvas.size() != sz:
            self.baseCanvas = QImage(sz, QImage.Format_RGB32)
            self.baseCanvas.fill(Qt.white)
            self._mark_composite_dirty()

        if self.drawingLayer is None or self.drawingLayer.size() != sz:
            self.drawingLayer = QImage(sz, QImage.Format_ARGB32_Premultiplied)
            self.drawingLayer.fill(Qt.transparent)
            self._mark_composite_dirty()

        if self.image.size() != sz:
            self.image = QImage(sz, QImage.Format_RGB32)
            self.image.fill(Qt.white)
            self._mark_composite_dirty()

    def _rescale_base_from_source(self):
        """Rebuild baseCanvas from sourceImageOriginal to fit current canvas, preserving aspect ratio."""
        self._ensure_layers()
        self.baseCanvas.fill(Qt.white)
        self.baseTargetRect = QRect()
        if self.sourceImageOriginal is None or self.sourceImageOriginal.isNull():
            self._mark_composite_dirty()
            return

        canvas_size = self._canvasSize
        src = self.sourceImageOriginal
        scaled_size = src.size().scaled(canvas_size, Qt.KeepAspectRatio)
        x = (canvas_size.width() - scaled_size.width()) // 2
        y = (canvas_size.height() - scaled_size.height()) // 2
        self.baseTargetRect = QRect(x, y, scaled_size.width(), scaled_size.height())

        p = QPainter(self.baseCanvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(self.baseTargetRect, src)
        p.end()
        self._mark_composite_dirty()

    def _recompose(self):
        """Compose final canvas image from baseCanvas + drawingLayer."""
        self._ensure_layers()
        self.image.fill(Qt.white)
        p = QPainter(self.image)
        p.drawImage(QPoint(0, 0), self.baseCanvas)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawImage(QPoint(0, 0), self.drawingLayer)
        p.end()
        self.originalImage = self.image

    def _snapshot_state(self):
        """Create a full snapshot for undo."""
        state = {
            'image': QImage(self.image),
            'base': QImage(self.baseCanvas) if self.baseCanvas is not None else None,
            'draw': QImage(self.drawingLayer) if self.drawingLayer is not None else None,
            'src': QImage(self.sourceImageOriginal) if self.sourceImageOriginal is not None else None,
            'canvas_size': QSize(self._canvasSize.width(), self._canvasSize.height()),
            'baseRect': QRect(self.baseTargetRect),
        }
        return state

    def _apply_state(self, state):
        """
        Apply a snapshot (used by undo/redo).

        :param state: State dict from _snapshot_state()
        """
        if not state:
            return

        target_canvas_size = state.get('canvas_size', None)
        if isinstance(target_canvas_size, QSize) and target_canvas_size.isValid():
            old_canvas = QSize(self._canvasSize)
            self._canvasSize = QSize(target_canvas_size)

            self.image = QImage(state['image']) if state['image'] is not None else QImage(self._canvasSize, QImage.Format_RGB32)
            if self.image.size() != self._canvasSize:
                self.image = self.image.scaled(self._canvasSize, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

            if state['base'] is not None:
                self.baseCanvas = QImage(state['base'])
            else:
                self.baseCanvas = QImage(self._canvasSize, QImage.Format_RGB32)
                self.baseCanvas.fill(Qt.white)

            if state['draw'] is not None:
                self.drawingLayer = QImage(state['draw'])
            else:
                self.drawingLayer = QImage(self._canvasSize, QImage.Format_ARGB32_Premultiplied)
                self.drawingLayer.fill(Qt.transparent)

            self.sourceImageOriginal = QImage(state['src']) if state['src'] is not None else None
            self.baseTargetRect = QRect(state['baseRect']) if state['baseRect'] is not None else QRect()

            self._mark_composite_dirty()
            self._update_widget_size_from_zoom()
            self.update()

    def _is_fit_available(self) -> bool:
        """
        Return True if there are letterbox margins that can be trimmed.
        Uses lightweight checks to avoid heavy full-image scans during menu opening.

        :return: True if fit action is available
        """
        # If the scaled source does not cover the whole canvas, trimming is possible
        if self.baseTargetRect.isValid() and not self.baseTargetRect.isNull():
            if self.baseTargetRect.width() < self._canvasSize.width() or self.baseTargetRect.height() < self._canvasSize.height():
                return True

        # Otherwise, if there is any non-transparent stroke content that doesn't span entire canvas, fit may trim
        bounds = self._detect_nontransparent_bounds(self.drawingLayer)
        if bounds is not None:
            return bounds.width() < self._canvasSize.width() or bounds.height() < self._canvasSize.height()
        return False

    def _compute_fit_rect(self) -> QRect | None:
        """
        Compute a fit rectangle based on the scaled source rect and drawn content.
        This avoids recomposing a full image and scanning all pixels in RGB.
        """
        if self._canvasSize.isEmpty():
            return None
        canvas_rect = QRect(0, 0, self._canvasSize.width(), self._canvasSize.height())
        result = None

        if self.baseTargetRect.isValid() and not self.baseTargetRect.isNull():
            result = self.baseTargetRect.intersected(canvas_rect)

        draw_bounds = self._detect_nontransparent_bounds(self.drawingLayer)
        if draw_bounds is not None and not draw_bounds.isNull():
            result = draw_bounds if result is None else result.united(draw_bounds)

        if result is None or result.isNull():
            return None
        return result

    def action_fit(self):
        """Trim white letterbox margins and resize canvas to the scaled image area. Undo-safe."""
        # Use lightweight fit computation
        fit_rect = self._compute_fit_rect()
        if fit_rect is None:
            return

        if fit_rect.width() == self._canvasSize.width() and fit_rect.height() == self._canvasSize.height():
            return

        self.saveForUndo()
        self._ensure_layers()

        new_base = self.baseCanvas.copy(fit_rect)
        new_draw = self.drawingLayer.copy(fit_rect)

        self._pendingResizeApply = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }
        self._mark_composite_dirty()

        self.window.controller.painter.common.change_canvas_size(f"{fit_rect.width()}x{fit_rect.height()}")
        self.update()

    def _detect_nonwhite_bounds(self, img: QImage, threshold: int = 250) -> QRect | None:
        """
        Detect tight bounding rect of non-white content in a composited image.
        A pixel is considered background if all channels >= threshold.
        Returns None if no non-white content is found.

        :param img: Image to analyze
        :param threshold: Threshold for considering a pixel as background (0-255)
        :return: QRect of non-white content or None
        """
        if img is None or img.isNull():
            return None

        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return None

        def is_bg(px: QColor) -> bool:
            return px.red() >= threshold and px.green() >= threshold and px.blue() >= threshold

        left = 0
        found = False
        for x in range(w):
            for y in range(h):
                if not is_bg(img.pixelColor(x, y)):
                    left = x
                    found = True
                    break
            if found:
                break
        if not found:
            return None  # all white

        right = w - 1
        found = False
        for x in range(w - 1, -1, -1):
            for y in range(h):
                if not is_bg(img.pixelColor(x, y)):
                    right = x
                    found = True
                    break
            if found:
                break

        top = 0
        found = False
        for y in range(h):
            for x in range(left, right + 1):
                if not is_bg(img.pixelColor(x, y)):
                    top = y
                    found = True
                    break
            if found:
                break

        bottom = h - 1
        found = False
        for y in range(h - 1, -1, -1):
            for x in range(left, right + 1):
                if not is_bg(img.pixelColor(x, y)):
                    bottom = y
                    found = True
                    break
            if found:
                break

        if right < left or bottom < top:
            return None

        return QRect(left, top, right - left + 1, bottom - top + 1)

    def _detect_nontransparent_bounds(self, img: QImage) -> QRect | None:
        """
        Fast bounds detection for drawing layer: scans alpha channel only.

        :param img: ARGB image
        :return: QRect of non-transparent content or None
        """
        if img is None or img.isNull():
            return None
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return None

        left = -1
        for x in range(w):
            for y in range(h):
                if img.pixelColor(x, y).alpha() > 0:
                    left = x
                    break
            if left != -1:
                break
        if left == -1:
            return None

        right = -1
        for x in range(w - 1, -1, -1):
            for y in range(h):
                if img.pixelColor(x, y).alpha() > 0:
                    right = x
                    break
            if right != -1:
                break

        top = -1
        for y in range(h):
            for x in range(left, right + 1):
                if img.pixelColor(x, y).alpha() > 0:
                    top = y
                    break
            if top != -1:
                break

        bottom = -1
        for y in range(h - 1, -1, -1):
            for x in range(left, right + 1):
                if img.pixelColor(x, y).alpha() > 0:
                    bottom = y
                    break
            if bottom != -1:
                break

        if right < left or bottom < top:
            return None
        return QRect(left, top, right - left + 1, bottom - top + 1)

    # ---------- Public API (clipboard, file, actions) ----------

    def handle_paste(self):
        """Handle clipboard paste"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if source.hasImage():
            image = clipboard.image()
            if isinstance(image, QImage):
                self.set_image(image, fit_canvas_to_image=True)

    def handle_copy(self):
        """Handle clipboard copy"""
        self._ensure_composited_image()
        clipboard = QApplication.clipboard()
        clipboard.setImage(self.image)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        self._act_undo.setEnabled(self.has_undo())
        self._act_redo.setEnabled(self.has_redo())

        # Enable paste based on clipboard; avoid heavy 'fit' checks here to keep menu snappy
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        self._act_paste.setEnabled(bool(mime_data.hasImage()))

        # Keep Fit enabled; the action validates availability when executed
        self._act_fit.setEnabled(True)

        self._ctx_menu.exec(event.globalPos())

    def action_open(self):
        """Open the image"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if path:
            self.open_image(path)

    def action_capture(self):
        """Capture the image"""
        self.saveForUndo()
        self.window.controller.painter.capture.use()

    def action_save(self):
        """Save image to file"""
        self._ensure_composited_image()
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            name,
            "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ",
        )
        if path:
            self.image.save(path)

    def action_clear(self):
        """Clear the image"""
        self.saveForUndo()
        self.clear_image()
        self.originalImage = self.image

    def open_image(self, path):
        """
        Open the image

        :param path: Path to image
        """
        img = QImage(path)
        if img.isNull():
            QMessageBox.information(self, "Image Loader", "Cannot load file.")
            return
        self.set_image(img, fit_canvas_to_image=True)

    def load_flat_image(self, path):
        """
        Load a flat image from file as current source.
        This is used for session restore; it does not enforce canvas resize now.

        :param path: Path to image
        """
        img = QImage(path)
        if img.isNull():
            return
        self.sourceImageOriginal = QImage(img)
        if self._canvasSize.width() > 0 and self._canvasSize.height() > 0:
            self._ensure_layers()
            self._rescale_base_from_source()
            self.drawingLayer.fill(Qt.transparent)
            self._mark_composite_dirty()
        else:
            pass

    def set_image(self, image, fit_canvas_to_image: bool = False):
        """
        Set image (as new original source)

        :param image: Image
        :param fit_canvas_to_image: True = set canvas size to image size (custom)
        """
        if image.isNull():
            return
        self.saveForUndo()
        self.sourceImageOriginal = QImage(image)
        if fit_canvas_to_image:
            w, h = image.width(), image.height()
            self.window.controller.painter.common.change_canvas_size(f"{w}x{h}")
        else:
            self._ensure_layers()
            self._rescale_base_from_source()
            self.drawingLayer.fill(Qt.transparent)
            self._mark_composite_dirty()
        self.update()

    def scale_to_fit(self, image):
        """
        Backward-compatibility wrapper. Uses layered model now.

        :param image: Image
        """
        self.set_image(image, fit_canvas_to_image=False)

    # ---------- Undo/redo ----------

    def saveForUndo(self):
        """Save current state for undo"""
        self._ensure_layers()
        self._ensure_composited_image()
        self.undoStack.append(self._snapshot_state())
        self.redoStack.clear()

    def undo(self):
        """Undo the last action"""
        if self.undoStack:
            current = self._snapshot_state()
            self.redoStack.append(current)
            state = self.undoStack.pop()
            self._apply_state(state)
            if self.window and hasattr(self.window, "controller"):
                self.window.controller.painter.common.sync_canvas_combo_from_widget()

    def redo(self):
        """Redo the last undo action"""
        if self.redoStack:
            current = self._snapshot_state()
            self.undoStack.append(current)
            state = self.redoStack.pop()
            self._apply_state(state)
            if self.window and hasattr(self.window, "controller"):
                self.window.controller.painter.common.sync_canvas_combo_from_widget()

    def has_undo(self) -> bool:
        """
        Check if undo is available

        :return: True if undo is available
        """
        return bool(self.undoStack)

    def has_redo(self) -> bool:
        """
        Check if redo is available

        :return: True if redo is available
        """
        return bool(self.redoStack)

    def save_base(self, path: str, include_drawing: bool = False) -> bool:
        """
        Save high-quality base image:
        - If an original source is present, saves that (cropped if crop was applied).
        - If no source exists, falls back to saving the current composited canvas.
        - When include_drawing=True, composites the stroke layer onto the original at original resolution.
        Returns True on success.

        :param path: Path to save
        :param include_drawing: Whether to include drawing layer
        :return: True on success
        """
        if not path:
            return False

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass

        if self.sourceImageOriginal is not None and not self.sourceImageOriginal.isNull():
            if not include_drawing:
                return self._save_image_atomic(self.sourceImageOriginal, path)

            src = QImage(self.sourceImageOriginal)
            if self.drawingLayer is None or self.drawingLayer.isNull():
                return self._save_image_atomic(src, path)

            if self.baseTargetRect.isNull() or self.baseTargetRect.width() <= 0 or self.baseTargetRect.height() <= 0:
                return self._save_image_atomic(src, path)

            overlay_canvas_roi = self.drawingLayer.copy(self.baseTargetRect)
            overlay_hi = overlay_canvas_roi.scaled(
                src.size(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )

            result = QImage(src)
            p = QPainter(result)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.drawImage(QPoint(0, 0), overlay_hi)
            p.end()

            return self._save_image_atomic(result, path)

        self._ensure_composited_image()
        return self._save_image_atomic(self.image, path)

    def _save_image_atomic(self, img: QImage, path: str, fmt: str = None, quality: int = -1) -> bool:
        """
        Save an image atomically using QSaveFile. Returns True on success.

        :param img: Image
        :param path: Path to save
        :param fmt: Format (e.g. 'PNG', 'JPEG'); if None, inferred from file extension
        :param quality: Quality (0-100) or -1 for default
        :return: True on success
        """
        if img is None or img.isNull() or not path:
            return False

        if fmt is None:
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.jpg', '.jpeg'):
                fmt = 'JPEG'
            elif ext == '.bmp':
                fmt = 'BMP'
            elif ext == '.webp':
                fmt = 'WEBP'
            elif ext in ('.tif', '.tiff'):
                fmt = 'TIFF'
            else:
                fmt = 'PNG'

        f = QSaveFile(path)
        if not f.open(QIODevice.WriteOnly):
            return False

        ok = img.save(f, fmt, quality)
        if not ok:
            f.cancelWriting()
            return False

        return f.commit()

    # ---------- Brush/eraser ----------

    def set_mode(self, mode: str):
        """
        Set painting mode: "brush" or "erase"

        :param mode: Mode
        """
        if mode not in ("brush", "erase"):
            return
        self._mode = mode
        if self._mode == "erase":
            self.setCursor(QCursor(Qt.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CrossCursor))

    def set_brush_color(self, color):
        """
        Set the brush color

        :param color: Color
        """
        self.brushColor = color
        self._pen.setColor(color)

    def set_brush_size(self, size):
        """
        Set the brush size

        :param size: Brush size
        """
        self.brushSize = size
        self._pen.setWidth(size)

    def clear_image(self):
        """Clear the image (both background and drawing layer)"""
        self._ensure_layers()
        self.sourceImageOriginal = None
        self.baseCanvas.fill(Qt.white)
        self.drawingLayer.fill(Qt.transparent)
        self._mark_composite_dirty()
        self.update()

    # ---------- Crop tool ----------

    def start_crop(self):
        """Activate crop mode."""
        self.cropping = True
        self._selecting = False
        self._selectionRect = QRect()
        self.setCursor(QCursor(Qt.CrossCursor))
        self.update()

    def cancel_crop(self):
        """Cancel crop mode."""
        self.cropping = False
        self._selecting = False
        self._selectionRect = QRect()
        self._stop_autoscroll()
        self.unsetCursor()
        self.update()

    def _finalize_crop(self):
        """Finalize crop with current selection rectangle."""
        self._stop_autoscroll()
        if not self.cropping or self._selectionRect.isNull() or self._selectionRect.width() <= 1 or self._selectionRect.height() <= 1:
            self.cancel_crop()
            return

        self._ensure_layers()
        sel = self._selectionRect.normalized()

        new_base = self.baseCanvas.copy(sel)
        new_draw = self.drawingLayer.copy(sel)

        self._pendingResizeApply = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }
        self._mark_composite_dirty()

        if self.sourceImageOriginal is not None and not self.baseTargetRect.isNull():
            inter = sel.intersected(self.baseTargetRect)
            if inter.isValid() and not inter.isNull():
                sx_ratio = self.sourceImageOriginal.width() / self.baseTargetRect.width()
                sy_ratio = self.sourceImageOriginal.height() / self.baseTargetRect.height()

                dx = inter.x() - self.baseTargetRect.x()
                dy = inter.y() - self.baseTargetRect.y()

                sx = max(0, int(dx * sx_ratio))
                sy = max(0, int(dy * sy_ratio))
                sw = max(1, int(inter.width() * sx_ratio))
                sh = max(1, int(inter.height() * sy_ratio))
                if sx + sw > self.sourceImageOriginal.width():
                    sw = self.sourceImageOriginal.width() - sx
                if sy + sh > self.sourceImageOriginal.height():
                    sh = self.sourceImageOriginal.height() - sy
                if sw > 0 and sh > 0:
                    self.sourceImageOriginal = self.sourceImageOriginal.copy(sx, sy, sw, sh)
                else:
                    self.sourceImageOriginal = None
            else:
                self.sourceImageOriginal = None
        else:
            pass

        self.cropping = False
        self._selecting = False
        self._selectionRect = QRect()
        self.unsetCursor()

        self.window.controller.painter.common.change_canvas_size(f"{sel.width()}x{sel.height()}")
        self.update()

    # ---------- Auto-scroll while cropping (for scroll areas) ----------

    def _find_scroll_area(self):
        """Locate the nearest ancestor QAbstractScrollArea and cache references."""
        w = self.parentWidget()
        area = None
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                area = w
                break
            w = w.parentWidget()
        self._scrollArea = area
        self._scrollViewport = area.viewport() if area is not None else None

    def _calc_scroll_step(self, dist_to_edge: int, margin: int) -> int:
        """
        Compute a smooth step size (px per tick) based on proximity to the edge.
        Closer to the edge -> faster scroll, clamped to configured limits.

        :param dist_to_edge: Distance to the edge in pixels (0 = at edge)
        :param margin: Margin in pixels where autoscroll is active
        :return: Step size in pixels (positive integer)
        """
        if dist_to_edge < 0:
            dist_to_edge = 0
        if margin <= 0:
            return self._autoScrollMinSpeed
        ratio = 1.0 - min(1.0, dist_to_edge / float(margin))
        step = self._autoScrollMinSpeed + ratio * (self._autoScrollMaxSpeed - self._autoScrollMinSpeed)
        return max(self._autoScrollMinSpeed, min(self._autoScrollMaxSpeed, int(step)))

    def _start_autoscroll(self):
        """Start autoscroll timer if inside a scroll area and cropping is active."""
        self._find_scroll_area()
        if self._scrollArea is not None and self._scrollViewport is not None:
            if not self._autoScrollTimer.isActive():
                self._autoScrollTimer.start()

    def _stop_autoscroll(self):
        """Stop autoscroll timer and release mouse if grabbed."""
        if self._autoScrollTimer.isActive():
            self._autoScrollTimer.stop()
        self.releaseMouse()

    def _autoscroll_tick(self):
        """
        Periodic autoscroll while user drags the crop selection near viewport edges.
        Uses global cursor position -> viewport coords -> scrollbars.
        Also updates current selection end in widget coordinates.
        """
        if not (self.cropping and self._selecting):
            self._stop_autoscroll()
            return
        if self._scrollArea is None or self._scrollViewport is None:
            return

        vp = self._scrollViewport
        area = self._scrollArea

        global_pos = QCursor.pos()
        pos_vp = vp.mapFromGlobal(global_pos)

        margin = self._autoScrollMargin
        dx = 0
        dy = 0

        if pos_vp.x() < margin:
            dx = -self._calc_scroll_step(pos_vp.x(), margin)
        elif pos_vp.x() > vp.width() - margin:
            dist = max(0, vp.width() - pos_vp.x())
            dx = self._calc_scroll_step(dist, margin)

        if pos_vp.y() < margin:
            dy = -self._calc_scroll_step(pos_vp.y(), margin)
        elif pos_vp.y() > vp.height() - margin:
            dist = max(0, vp.height() - pos_vp.y())
            dy = self._calc_scroll_step(dist, margin)

        scrolled = False
        if dx != 0:
            hbar = area.horizontalScrollBar()
            if hbar is not None and hbar.maximum() > hbar.minimum():
                newv = max(hbar.minimum(), min(hbar.maximum(), hbar.value() + dx))
                if newv != hbar.value():
                    hbar.setValue(newv)
                    scrolled = True

        if dy != 0:
            vbar = area.verticalScrollBar()
            if vbar is not None and vbar.maximum() > vbar.minimum():
                newv = max(vbar.minimum(), min(vbar.maximum(), vbar.value() + dy))
                if newv != vbar.value():
                    vbar.setValue(newv)
                    scrolled = True

        if self._selecting:
            pos_widget = self.mapFromGlobal(global_pos)
            cx = min(max(0, pos_widget.x()), max(0, self.width() - 1))
            cy = min(max(0, pos_widget.y()), max(0, self.height() - 1))
            cpt = self._to_canvas_point(QPoint(cx, cy))
            self._selectionRect = QRect(self._selectionStart, cpt)
            if scrolled or dx != 0 or dy != 0:
                self.update()

    # ---------- Pan (middle mouse drag) ----------

    def _can_pan(self) -> bool:
        """
        Return True if widget is inside a scroll area and content is scrollable.
        """
        self._find_scroll_area()
        if self._scrollArea is None:
            return False
        hbar = self._scrollArea.horizontalScrollBar()
        vbar = self._scrollArea.verticalScrollBar()
        h_ok = hbar is not None and hbar.maximum() > hbar.minimum()
        v_ok = vbar is not None and vbar.maximum() > vbar.minimum()
        return h_ok or v_ok

    def _start_pan(self, global_pos: QPoint):
        """
        Begin view panning with middle mouse button.
        """
        if self._panning:
            return
        self._panning = True
        self._panLastGlobalPos = QPoint(global_pos)
        # Store current cursor to restore later
        self._cursorBeforePan = QCursor(self.cursor())
        # Use a closed hand to indicate grabbing the canvas
        self.setCursor(QCursor(Qt.ClosedHandCursor))
        self.grabMouse()

    def _update_pan(self, global_pos: QPoint):
        """
        Update scrollbars based on mouse movement delta in global coordinates.
        """
        if not self._panning or self._scrollArea is None:
            return
        dx = global_pos.x() - self._panLastGlobalPos.x()
        dy = global_pos.y() - self._panLastGlobalPos.y()
        self._panLastGlobalPos = QPoint(global_pos)

        hbar = self._scrollArea.horizontalScrollBar()
        vbar = self._scrollArea.verticalScrollBar()

        # Dragging the content to the right should reveal the left side -> subtract deltas
        if hbar is not None and hbar.maximum() > hbar.minimum():
            hbar.setValue(int(max(hbar.minimum(), min(hbar.maximum(), hbar.value() - dx))))
        if vbar is not None and vbar.maximum() > vbar.minimum():
            vbar.setValue(int(max(vbar.minimum(), min(vbar.maximum(), vbar.value() - dy))))

    def _end_pan(self):
        """
        End panning and restore previous cursor.
        """
        if not self._panning:
            return
        self._panning = False
        self.releaseMouse()
        try:
            if self._cursorBeforePan is not None:
                # Restore previous cursor (do not guess based on mode/crop)
                self.setCursor(self._cursorBeforePan)
        finally:
            self._cursorBeforePan = None

    # ---------- Events ----------

    def wheelEvent(self, event):
        """
        CTRL + wheel => zoom. Regular scrolling falls back to default behavior.

        :param event: Event
        """
        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in_step()
            elif delta < 0:
                self.zoom_out_step()
            event.accept()
            return
        super().wheelEvent(event)

    def _dirty_canvas_rect_for_point(self, pt_canvas: QPoint, pen_width: int) -> QRect:
        """Compute dirty canvas rect around a single painted point."""
        r = max(1, int(math.ceil(pen_width / 2))) + 2
        return QRect(pt_canvas.x() - r, pt_canvas.y() - r, 2 * r + 1, 2 * r + 1)

    def _dirty_canvas_rect_for_segment(self, a: QPoint, b: QPoint, pen_width: int) -> QRect:
        """Compute dirty canvas rect for a line segment between two canvas points."""
        x1 = min(a.x(), b.x())
        y1 = min(a.y(), b.y())
        x2 = max(a.x(), b.x())
        y2 = max(a.y(), b.y())
        pad = max(1, int(math.ceil(pen_width / 2))) + 2
        return QRect(x1 - pad, y1 - pad, (x2 - x1) + 2 * pad + 1, (y2 - y1) + 2 * pad + 1)

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        # Middle button: start panning if scrollable
        if event.button() == Qt.MiddleButton:
            if not (self.cropping and self._selecting) and not self.drawing and self._can_pan():
                gp = event.globalPosition().toPoint()
                self._start_pan(gp)
                event.accept()
                return

        if event.button() == Qt.LeftButton:
            self._mouseDown = True
            if self.cropping:
                self.saveForUndo()
                self._selecting = True
                self._selectionStart = self._to_canvas_point(event.position())
                self._selectionRect = QRect(self._selectionStart, self._selectionStart)
                self.update()
                self.grabMouse()
                self._start_autoscroll()
                return

            self._ensure_layers()
            self.drawing = True
            self.lastPointCanvas = self._to_canvas_point(event.position())
            self.saveForUndo()

            p = QPainter(self.drawingLayer)
            p.setRenderHint(QPainter.Antialiasing, True)
            if self._mode == "erase":
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen(Qt.transparent, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                p.setPen(pen)
            else:
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.setPen(self._pen)
            p.drawPoint(self.lastPointCanvas)
            p.end()
            self._mark_composite_dirty()

            # Update only the affected region
            dirty_canvas = self._dirty_canvas_rect_for_point(self.lastPointCanvas, self.brushSize)
            self.update(self._from_canvas_rect(dirty_canvas))

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        # Update panning if active
        if self._panning and (event.buttons() & Qt.MiddleButton):
            gp = event.globalPosition().toPoint()
            self._update_pan(gp)
            event.accept()
            return

        if self.cropping and self._selecting and (event.buttons() & Qt.LeftButton):
            self._selectionRect = QRect(self._selectionStart, self._to_canvas_point(event.position()))
            self.update()
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            self._ensure_layers()
            cur = self._to_canvas_point(event.position())
            p = QPainter(self.drawingLayer)
            p.setRenderHint(QPainter.Antialiasing, True)
            if self._mode == "erase":
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen(Qt.transparent, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                p.setPen(pen)
            else:
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.setPen(self._pen)
            p.drawLine(self.lastPointCanvas, cur)
            p.end()
            self._mark_composite_dirty()

            # Update only the affected region for this segment
            dirty_canvas = self._dirty_canvas_rect_for_segment(self.lastPointCanvas, cur, self.brushSize)
            self.lastPointCanvas = cur
            self.update(self._from_canvas_rect(dirty_canvas))

    def mouseReleaseEvent(self, event):
        """
        Mouse release event

        :param event: Event
        """
        # End panning on middle button release
        if event.button() == Qt.MiddleButton:
            self._end_pan()
            event.accept()
            return

        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._mouseDown = False
            if self.cropping and self._selecting:
                self._finalize_crop()
            self.drawing = False

    def keyPressEvent(self, event):
        """
        Key press event to handle shortcuts

        :param event: Event
        """
        if event.key() == Qt.Key_Z and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key_V and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.handle_paste()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.cropping and self._selecting:
                self._finalize_crop()
        elif event.key() == Qt.Key_Escape:
            if self.cropping:
                self.cancel_crop()

    def paintEvent(self, event):
        """
        Paint event (draw)

        :param event: Event
        """
        # Ensure layers are valid; avoid recomposing the full image here.
        if self.baseCanvas is None or self.drawingLayer is None:
            self._ensure_layers()

        p = QPainter(self)

        # Paint only the region requested by Qt; map it to canvas to avoid scaling the whole image.
        target_rect = event.rect()
        if not target_rect.isNull():
            src_rect = self._widget_rect_to_canvas_rect(target_rect)
            if not src_rect.isNull():
                # Draw base
                p.drawImage(target_rect, self.baseCanvas, src_rect)
                # Draw strokes on top
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.drawImage(target_rect, self.drawingLayer, src_rect)

        # Draw crop overlay if active (convert canvas selection to display coords)
        if self.cropping and not self._selectionRect.isNull():
            sel = self._selectionRect.normalized()
            sel_view = self._from_canvas_rect(sel)
            overlay = QColor(0, 0, 0, 120)
            W, H = self.width(), self.height()

            if sel_view.left() > 0:
                p.fillRect(0, 0, sel_view.left(), H, overlay)
            if sel_view.right() < W - 1:
                p.fillRect(sel_view.right() + 1, 0, W - (sel_view.right() + 1), H, overlay)
            if sel_view.top() > 0:
                p.fillRect(sel_view.left(), 0, sel_view.width(), sel_view.top(), overlay)
            if sel_view.bottom() < H - 1:
                p.fillRect(sel_view.left(), sel_view.bottom() + 1, sel_view.width(), H - (sel_view.bottom() + 1), overlay)

            p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
            p.drawRect(sel_view.adjusted(0, 0, -1, -1))

        p.end()
        # Leave self.image stale until explicitly requested; avoids recomposition on every frame.

    def resizeEvent(self, event):
        """
        Update layers on canvas size change; ignore layout/display resizes unless explicitly requested.
        Only two kinds of resizes are acted upon:
        - canvas resize requested via set_canvas_size_pixels() -> _canvasResizeInProgress
        - display-only resizes initiated by zoom -> _zoomResizeInProgress
        Any other widget/layout resize will be ignored for canvas logic.
        """
        new_widget_size = event.size()

        # Explicit logical canvas resize requested by controller
        if self._canvasResizeInProgress:
            # Already updated _canvasSize in setter; ensure display size is in sync
            self._update_widget_size_from_zoom()
            super().resizeEvent(event)
            return

        # Display-only resize caused by zoom update: nothing to do with buffers
        if self._zoomResizeInProgress:
            self.update()
            super().resizeEvent(event)
            return

        # Ignore stray layout-driven resizes; enforce current display size from zoom
        self._update_widget_size_from_zoom()
        self.update()
        super().resizeEvent(event)

    def _handle_canvas_resized(self, old_size: QSize, new_size: QSize):
        """
        Apply buffer updates when the logical canvas size changes.

        :param old_size: Previous canvas size
        :param new_size: New canvas size
        """
        self._ensure_layers()

        if self._pendingResizeApply is not None:
            new_base = self._pendingResizeApply.get('base')
            new_draw = self._pendingResizeApply.get('draw')

            # Reset layers to new canvas size
            self.baseCanvas = QImage(new_size, QImage.Format_RGB32)
            self.baseCanvas.fill(Qt.white)
            self.drawingLayer = QImage(new_size, QImage.Format_ARGB32_Premultiplied)
            self.drawingLayer.fill(Qt.transparent)

            if new_base is not None:
                if new_base.size() == new_size:
                    self.baseCanvas = QImage(new_base)
                else:
                    bx = (new_size.width() - new_base.width()) // 2
                    by = (new_size.height() - new_base.height()) // 2
                    p = QPainter(self.baseCanvas)
                    p.drawImage(QPoint(max(0, bx), max(0, by)), new_base)
                    p.end()

            if new_draw is not None:
                if new_draw.size() == new_size:
                    self.drawingLayer = QImage(new_draw)
                else:
                    dx = (new_size.width() - new_draw.width()) // 2
                    dy = (new_size.height() - new_draw.height()) // 2
                    p = QPainter(self.drawingLayer)
                    p.drawImage(QPoint(max(0, dx), max(0, dy)), new_draw)
                    p.end()

            self._pendingResizeApply = None
            self.baseTargetRect = QRect(0, 0, self.baseCanvas.width(), self.baseCanvas.height())
            self._mark_composite_dirty()
        else:
            # Rebuild background from original source
            self._rescale_base_from_source()

            # Scale drawing content to new canvas size if previous canvas was valid
            if old_size.isValid() and (old_size.width() > 0 and old_size.height() > 0) and \
                    (self.drawingLayer is not None) and (self.drawingLayer.size() != new_size):
                self.drawingLayer = self.drawingLayer.scaled(new_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self._mark_composite_dirty()

        self.update()

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)