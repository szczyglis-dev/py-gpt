#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

import bisect
import math

from PySide6.QtCore import QTimer, Qt, QPoint, QPointF, QRect, QSize
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QAbstractScrollArea


class Viewport:
    """Painter viewport operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.zoom = 1.0
        self.min_zoom = 0.10    # 10%
        self.max_zoom = 10.0    # 1000%
        self.zoom_steps = [0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 5.00, 10.00]
        self.resizing = False  # guard used during display-size updates caused by zoom
        self.scroll_area = None
        self.scroll_viewport = None
        self.timer = QTimer(canvas)
        self.timer.setInterval(16)  # ~60 FPS, low overhead
        self.timer.timeout.connect(self.autoscroll_tick)
        self.margin = 36            # px from viewport edge to trigger autoscroll
        self.min_speed = 2           # px per tick (min)
        self.max_speed = 18          # px per tick (max)
        self.panning = False
        self.last_global_pos = QPoint()
        self.cursor_before_pan = None  # store/restore cursor shape while panning

    def on_zoom_changed(self, text: str):
        """
        Slot for a zoom ComboBox change. Accepts strings like "100%" or "150 %".

        :param text: Text from the combo box
        """
        canvas = self.canvas
        val = self.parse_percent(text)
        if val is None:
            return
        # Use viewport center as anchor when changed from combobox
        anchor = self.viewport_center_in_widget_coords()
        self.set_zoom(val / 100.0, anchor_widget_pos=anchor)

    def set_percent(self, percent: int):
        """
        Set zoom using percent value, e.g. 150 for 150%.

        :param percent: Zoom in percent
        """
        canvas = self.canvas
        anchor = self.viewport_center_in_widget_coords()
        self.set_zoom(max(1, percent) / 100.0, anchor_widget_pos=anchor)

    def percent(self) -> int:
        """
        Return current zoom as integer percent.

        :return: Zoom in percent (e.g. 150 for 150%)
        """
        canvas = self.canvas
        return int(round(self.zoom * 100.0))

    def steps(self) -> list[int]:
        """
        Return recommended preset zoom steps in percent for a combo-box.

        :return: List of zoom steps in percent
        """
        canvas = self.canvas
        return [int(round(z * 100)) for z in self.zoom_steps]

    def set_zoom(self, zoom: float, anchor_widget_pos: QPointF | None = None, emit_signal: bool = True):
        """
        Set zoom to an absolute factor. View-only; does not touch canvas resolution.
        anchor_widget_pos: QPointF in widget coordinates; if None, viewport center is used.

        :param zoom: Zoom factor (e.g. 1.0 for 100%)
        :param anchor_widget_pos: Anchor point in widget coordinates to keep stable during zoom
        :param emit_signal: Whether to emit zoomChanged signal and sync combobox
        """
        canvas = self.canvas
        new_zoom = max(self.min_zoom, min(self.max_zoom, float(zoom)))
        if abs(new_zoom - self.zoom) < 1e-6:
            return

        old_zoom = self.zoom
        self.zoom = new_zoom

        # Sync UI (combobox) and emit signal
        if emit_signal:
            self.emit_zoom_changed()

        # Update display size and scroll to keep anchor stable
        if anchor_widget_pos is None:
            anchor_widget_pos = self.viewport_center_in_widget_coords()
        self.update_widget_size_from_zoom()
        self.adjust_scroll_to_anchor(anchor_widget_pos, old_zoom, self.zoom)
        canvas.text.sync_style(canvas, refocus=False)

        canvas.update()

    def zoom_in_step(self):
        """Increase zoom to next preset step."""
        canvas = self.canvas
        idx = self.nearest_zoom_step_index(self.zoom)
        if idx < len(self.zoom_steps) - 1:
            self.set_zoom(self.zoom_steps[idx + 1], anchor_widget_pos=self.cursor_pos_in_widget())

    def zoom_out_step(self):
        """Decrease zoom to previous preset step."""
        canvas = self.canvas
        idx = self.nearest_zoom_step_index(self.zoom)
        if idx > 0:
            self.set_zoom(self.zoom_steps[idx - 1], anchor_widget_pos=self.cursor_pos_in_widget())

    def emit_zoom_changed(self):
        """Emit signal and try to sync external combobox via controller if available."""
        canvas = self.canvas
        canvas.zoomChanged.emit(self.zoom)

    def nearest_zoom_step_index(self, z: float) -> int:
        """
        Find index of the nearest step to z in _zoomSteps.

        :param z: Zoom factor
        :return: Index of the nearest zoom step
        """
        canvas = self.canvas
        steps = self.zoom_steps
        pos = bisect.bisect_left(steps, z)
        if pos == 0:
            return 0
        if pos >= len(steps):
            return len(steps) - 1
        before = steps[pos - 1]
        after = steps[pos]
        return pos if abs(after - z) < abs(z - before) else pos - 1

    def cursor_pos_in_widget(self) -> QPointF:
        """
        Return current cursor position in widget coordinates.

        :return: QPointF in widget coordinates
        """
        canvas = self.canvas
        return QPointF(canvas.mapFromGlobal(QCursor.pos()))

    def viewport_center_in_widget_coords(self) -> QPointF:
        """
        Return viewport center mapped to widget coordinates; falls back to widget center.

        :return: QPointF in widget coordinates
        """
        canvas = self.canvas
        self.find_scroll_area()
        if self.scroll_viewport is not None:
            vp = self.scroll_viewport
            center_vp = QPointF(vp.width() / 2.0, vp.height() / 2.0)
            return QPointF(canvas.mapFrom(vp, center_vp.toPoint()))
        return QPointF(canvas.width() / 2.0, canvas.height() / 2.0)

    def adjust_scroll_to_anchor(self, anchor_widget_pos: QPointF, old_zoom: float, new_zoom: float):
        """
        Adjust scrollbars to keep the anchor point stable in viewport during zoom.

        :param anchor_widget_pos: Anchor point in widget coordinates
        :param old_zoom: Previous zoom factor
        :param new_zoom: New zoom factor
        """
        canvas = self.canvas
        self.find_scroll_area()
        if self.scroll_area is None or self.scroll_viewport is None:
            return
        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        if hbar is None and vbar is None:
            return
        scale = new_zoom / max(1e-6, old_zoom)
        dx = anchor_widget_pos.x() * (scale - 1.0)
        dy = anchor_widget_pos.y() * (scale - 1.0)
        if hbar is not None:
            hbar.setValue(int(round(hbar.value() + dx)))
        if vbar is not None:
            vbar.setValue(int(round(vbar.value() + dy)))

    def update_widget_size_from_zoom(self):
        """Resize display widget to reflect current zoom; leaves canvas buffers untouched."""
        canvas = self.canvas
        disp_w = max(1, int(round(canvas.document.canvas_size.width() * self.zoom)))
        disp_h = max(1, int(round(canvas.document.canvas_size.height() * self.zoom)))
        new_disp = QSize(disp_w, disp_h)
        if canvas.size() == new_disp:
            return
        self.resizing = True
        try:
            # setFixedSize is preferred for content widgets inside scroll areas
            canvas.setFixedSize(new_disp)
        finally:
            self.resizing = False

    def to_canvas_point(self, pt) -> QPoint:
        """
        Map a widget point (QPoint or QPointF) to canvas coordinates.

        :param pt: QPoint or QPointF in widget coordinates
        :return: QPoint in canvas coordinates
        """
        canvas = self.canvas
        if isinstance(pt, QPointF):
            x = int(round(pt.x() / self.zoom))
            y = int(round(pt.y() / self.zoom))
        else:
            x = int(round(pt.x() / self.zoom))
            y = int(round(pt.y() / self.zoom))
        x = max(0, min(canvas.document.canvas_size.width() - 1, x))
        y = max(0, min(canvas.document.canvas_size.height() - 1, y))
        return QPoint(x, y)

    def from_canvas_rect(self, rc: QRect) -> QRect:
        """
        Map a canvas rect to widget/display coordinates.

        :param rc: QRect in canvas coordinates
        :return: QRect in widget coordinates
        """
        canvas = self.canvas
        x = int(round(rc.x() * self.zoom))
        y = int(round(rc.y() * self.zoom))
        w = int(round(rc.width() * self.zoom))
        h = int(round(rc.height() * self.zoom))
        return QRect(x, y, w, h)

    def widget_rect_to_canvas_rect(self, rc: QRect) -> QRect:
        """
        Map a widget rect (in display pixels) to a canvas rect (in canvas pixels).
        Uses floor/ceil to ensure coverage and clamps to canvas bounds.
        """
        canvas = self.canvas
        if rc.isNull() or rc.width() <= 0 or rc.height() <= 0:
            return QRect()
        inv = 1.0 / max(1e-6, self.zoom)
        x1 = int(math.floor(rc.x() * inv))
        y1 = int(math.floor(rc.y() * inv))
        x2 = int(math.ceil((rc.x() + rc.width()) * inv))
        y2 = int(math.ceil((rc.y() + rc.height()) * inv))
        x1 = max(0, min(canvas.document.canvas_size.width(), x1))
        y1 = max(0, min(canvas.document.canvas_size.height(), y1))
        x2 = max(0, min(canvas.document.canvas_size.width(), x2))
        y2 = max(0, min(canvas.document.canvas_size.height(), y2))
        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        return QRect(x1, y1, w, h)

    def parse_percent(self, text: str) -> int | None:
        """
        Parse '150%' -> 150.

        Returns None if parsing fails.

        :param text: Text to parse
        :return: Integer percent or None
        """
        canvas = self.canvas
        if not text:
            return None
        try:
            s = text.strip().replace('%', '').strip()
            s = s.replace(',', '.')
            valf = float(s)
            return int(round(valf))
        except Exception:
            return None

    def find_scroll_area(self):
        """Locate the nearest ancestor QAbstractScrollArea and cache references."""
        canvas = self.canvas
        w = canvas.parentWidget()
        area = None
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                area = w
                break
            w = w.parentWidget()
        self.scroll_area = area
        self.scroll_viewport = area.viewport() if area is not None else None

    def calc_scroll_step(self, dist_to_edge: int, margin: int) -> int:
        """
        Compute a smooth step size (px per tick) based on proximity to the edge.
        Closer to the edge -> faster scroll, clamped to configured limits.

        :param dist_to_edge: Distance to the edge in pixels (0 = at edge)
        :param margin: Margin in pixels where autoscroll is active
        :return: Step size in pixels (positive integer)
        """
        canvas = self.canvas
        if dist_to_edge < 0:
            dist_to_edge = 0
        if margin <= 0:
            return self.min_speed
        ratio = 1.0 - min(1.0, dist_to_edge / float(margin))
        step = self.min_speed + ratio * (self.max_speed - self.min_speed)
        return max(self.min_speed, min(self.max_speed, int(step)))

    def start_autoscroll(self):
        """Start autoscroll timer if inside a scroll area and cropping is active."""
        canvas = self.canvas
        self.find_scroll_area()
        if self.scroll_area is not None and self.scroll_viewport is not None:
            if not self.timer.isActive():
                self.timer.start()

    def stop_autoscroll(self):
        """Stop autoscroll timer and release mouse if grabbed."""
        canvas = self.canvas
        if self.timer.isActive():
            self.timer.stop()
        canvas.releaseMouse()

    def autoscroll_tick(self):
        """
        Periodic autoscroll while user drags the crop selection near viewport edges.
        Uses global cursor position -> viewport coords -> scrollbars.
        Also updates current selection end in widget coordinates.
        """
        canvas = self.canvas
        if not (canvas.selection.active and canvas.selection.selecting):
            self.stop_autoscroll()
            return
        if self.scroll_area is None or self.scroll_viewport is None:
            return

        vp = self.scroll_viewport
        area = self.scroll_area

        global_pos = QCursor.pos()
        pos_vp = vp.mapFromGlobal(global_pos)

        margin = self.margin
        dx = 0
        dy = 0

        if pos_vp.x() < margin:
            dx = -self.calc_scroll_step(pos_vp.x(), margin)
        elif pos_vp.x() > vp.width() - margin:
            dist = max(0, vp.width() - pos_vp.x())
            dx = self.calc_scroll_step(dist, margin)

        if pos_vp.y() < margin:
            dy = -self.calc_scroll_step(pos_vp.y(), margin)
        elif pos_vp.y() > vp.height() - margin:
            dist = max(0, vp.height() - pos_vp.y())
            dy = self.calc_scroll_step(dist, margin)

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

        if canvas.selection.selecting:
            pos_widget = canvas.mapFromGlobal(global_pos)
            cx = min(max(0, pos_widget.x()), max(0, canvas.width() - 1))
            cy = min(max(0, pos_widget.y()), max(0, canvas.height() - 1))
            cpt = self.to_canvas_point(QPoint(cx, cy))
            canvas.selection.rect = QRect(canvas.selection.start_point, cpt)
            if scrolled or dx != 0 or dy != 0:
                canvas.update()

    def can_pan(self) -> bool:
        """
        Return True if widget is inside a scroll area and content is scrollable.
        """
        canvas = self.canvas
        self.find_scroll_area()
        if self.scroll_area is None:
            return False
        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        h_ok = hbar is not None and hbar.maximum() > hbar.minimum()
        v_ok = vbar is not None and vbar.maximum() > vbar.minimum()
        return h_ok or v_ok

    def start_pan(self, global_pos: QPoint):
        """
        Begin view panning with middle mouse button.
        """
        canvas = self.canvas
        if self.panning:
            return
        self.panning = True
        self.last_global_pos = QPoint(global_pos)
        # Store current cursor to restore later
        self.cursor_before_pan = QCursor(canvas.cursor())
        # Use a closed hand to indicate grabbing the canvas
        canvas.setCursor(QCursor(Qt.ClosedHandCursor))
        canvas.grabMouse()

    def update_pan(self, global_pos: QPoint):
        """
        Update scrollbars based on mouse movement delta in global coordinates.
        """
        canvas = self.canvas
        if not self.panning or self.scroll_area is None:
            return
        dx = global_pos.x() - self.last_global_pos.x()
        dy = global_pos.y() - self.last_global_pos.y()
        self.last_global_pos = QPoint(global_pos)

        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()

        # Dragging the content to the right should reveal the left side -> subtract deltas
        if hbar is not None and hbar.maximum() > hbar.minimum():
            hbar.setValue(int(max(hbar.minimum(), min(hbar.maximum(), hbar.value() - dx))))
        if vbar is not None and vbar.maximum() > vbar.minimum():
            vbar.setValue(int(max(vbar.minimum(), min(vbar.maximum(), vbar.value() - dy))))

    def end_pan(self):
        """
        End panning and restore previous cursor.
        """
        canvas = self.canvas
        if not self.panning:
            return
        self.panning = False
        canvas.releaseMouse()
        try:
            if self.cursor_before_pan is not None:
                # Restore previous cursor (do not guess based on mode/crop)
                canvas.setCursor(self.cursor_before_pan)
        finally:
            self.cursor_before_pan = None

