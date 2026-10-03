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


from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QImage, QColor, QCursor


class Selection:
    """Painter selection operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.active = False
        self.selecting = False
        self.start_point = QPoint()
        self.rect = QRect()

    def is_fit_available(self) -> bool:
        """
        Return True if there are letterbox margins that can be trimmed.
        Uses lightweight checks to avoid heavy full-image scans during menu opening.

        :return: True if fit action is available
        """
        canvas = self.canvas
        # If the scaled source does not cover the whole canvas, trimming is possible
        if canvas.document.base_rect.isValid() and not canvas.document.base_rect.isNull():
            if canvas.document.base_rect.width() < canvas.document.canvas_size.width() or canvas.document.base_rect.height() < canvas.document.canvas_size.height():
                return True

        # Otherwise, if there is any non-transparent stroke content that doesn't span entire canvas, fit may trim
        bounds = self.detect_nontransparent_bounds(canvas.document.drawing)
        if bounds is not None:
            return bounds.width() < canvas.document.canvas_size.width() or bounds.height() < canvas.document.canvas_size.height()
        return False

    def compute_fit_rect(self) -> QRect | None:
        """
        Compute a fit rectangle based on the scaled source rect and drawn content.
        This avoids recomposing a full image and scanning all pixels in RGB.
        """
        canvas = self.canvas
        if canvas.document.canvas_size.isEmpty():
            return None
        canvas_rect = QRect(0, 0, canvas.document.canvas_size.width(), canvas.document.canvas_size.height())
        result = None

        if canvas.document.base_rect.isValid() and not canvas.document.base_rect.isNull():
            result = canvas.document.base_rect.intersected(canvas_rect)

        draw_bounds = self.detect_nontransparent_bounds(canvas.document.drawing)
        if draw_bounds is not None and not draw_bounds.isNull():
            result = draw_bounds if result is None else result.united(draw_bounds)

        if result is None or result.isNull():
            return None
        return result

    def fit(self):
        """Trim white letterbox margins and resize canvas to the scaled image area. Undo-safe."""
        canvas = self.canvas
        # Use lightweight fit computation
        fit_rect = self.compute_fit_rect()
        if fit_rect is None:
            return

        if fit_rect.width() == canvas.document.canvas_size.width() and fit_rect.height() == canvas.document.canvas_size.height():
            return

        canvas.history.push()
        canvas.document.ensure_layers()

        new_base = canvas.document.base.copy(fit_rect)
        new_draw = canvas.document.drawing.copy(fit_rect)

        canvas.document.pending_resize = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }
        canvas.document.mark_composite_dirty()

        canvas.tool.settings.change_canvas_size(f"{fit_rect.width()}x{fit_rect.height()}")
        canvas.update()

    def detect_nonwhite_bounds(self, img: QImage, threshold: int = 250) -> QRect | None:
        """
        Detect tight bounding rect of non-white content in a composited image.
        A pixel is considered background if all channels >= threshold.
        Returns None if no non-white content is found.

        :param img: Image to analyze
        :param threshold: Threshold for considering a pixel as background (0-255)
        :return: QRect of non-white content or None
        """
        canvas = self.canvas
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

    def detect_nontransparent_bounds(self, img: QImage) -> QRect | None:
        """
        Fast bounds detection for drawing layer: scans alpha channel only.

        :param img: ARGB image
        :return: QRect of non-transparent content or None
        """
        canvas = self.canvas
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

    def start(self):
        """Activate crop mode."""
        canvas = self.canvas
        canvas.text.commit(canvas)
        self.active = True
        self.selecting = False
        self.rect = QRect()
        canvas.setCursor(QCursor(Qt.CrossCursor))
        canvas.update()

    def cancel(self):
        """Cancel crop mode."""
        canvas = self.canvas
        self.active = False
        self.selecting = False
        self.rect = QRect()
        canvas.viewport.stop_autoscroll()
        canvas.unsetCursor()
        canvas.update()

    def finish(self):
        """Finalize crop with current selection rectangle."""
        canvas = self.canvas
        canvas.viewport.stop_autoscroll()
        if not self.active or self.rect.isNull():
            self.cancel()
            return

        # QRect keeps the drag direction. A selection drawn right-to-left or
        # bottom-to-top therefore has a negative width/height until normalized.
        # Validate only after normalization so cropping works in every direction.
        sel = self.rect.normalized()
        if sel.width() <= 1 or sel.height() <= 1:
            self.cancel()
            return

        canvas.document.ensure_layers()

        new_base = canvas.document.base.copy(sel)
        new_draw = canvas.document.drawing.copy(sel)

        canvas.document.pending_resize = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }
        canvas.document.mark_composite_dirty()

        if canvas.document.source_image is not None and not canvas.document.base_rect.isNull():
            inter = sel.intersected(canvas.document.base_rect)
            if inter.isValid() and not inter.isNull():
                sx_ratio = canvas.document.source_image.width() / canvas.document.base_rect.width()
                sy_ratio = canvas.document.source_image.height() / canvas.document.base_rect.height()

                dx = inter.x() - canvas.document.base_rect.x()
                dy = inter.y() - canvas.document.base_rect.y()

                sx = max(0, int(dx * sx_ratio))
                sy = max(0, int(dy * sy_ratio))
                sw = max(1, int(inter.width() * sx_ratio))
                sh = max(1, int(inter.height() * sy_ratio))
                if sx + sw > canvas.document.source_image.width():
                    sw = canvas.document.source_image.width() - sx
                if sy + sh > canvas.document.source_image.height():
                    sh = canvas.document.source_image.height() - sy
                if sw > 0 and sh > 0:
                    canvas.document.source_image = canvas.document.source_image.copy(sx, sy, sw, sh)
                else:
                    canvas.document.source_image = None
            else:
                canvas.document.source_image = None
        else:
            pass

        self.active = False
        self.selecting = False
        self.rect = QRect()
        canvas.unsetCursor()

        canvas.tool.settings.change_canvas_size(f"{sel.width()}x{sel.height()}")
        canvas.update()

