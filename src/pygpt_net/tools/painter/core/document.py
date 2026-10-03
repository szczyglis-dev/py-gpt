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


from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QMessageBox


class Document:
    """Painter document operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.canvas_size = QSize(max(1, canvas.width()), max(1, canvas.height()))
        self.resizing = False
        self.image = QImage(self.canvas_size, QImage.Format_RGB32)
        self.source_image = None
        self.base = None
        self.base_rect = QRect()
        self.drawing = None
        self.original_image = None  # kept for API compatibility; reflects current composited image
        self.pending_resize = None  # payload used after crop to apply exact pixels on resize
        self.dirty = True  # True => recomposition needed before exporting/copying

    def resize(self, width: int, height: int):
        """
        Explicitly set logical canvas size in pixels.
        This never depends on view zoom and never uses parent/layout resizes.

        :param width: canvas width in pixels
        :param height: canvas height in pixels
        """
        canvas = self.canvas
        w = max(1, int(width))
        h = max(1, int(height))

        if self.canvas_size.width() == w and self.canvas_size.height() == h:
            # Keep display size consistent with current zoom
            canvas.viewport.update_widget_size_from_zoom()
            return

        old_canvas = QSize(self.canvas_size)
        self.canvas_size = QSize(w, h)

        self.resizing = True
        try:
            self.handle_canvas_resized(old_canvas, self.canvas_size)
            # After logical resize, update the displayed size according to zoom
            canvas.viewport.update_widget_size_from_zoom()
        finally:
            self.resizing = False

    def size(self) -> QSize:
        """
        Return current logical canvas size (pixels).

        :return: QSize of canvas
        """
        canvas = self.canvas
        return QSize(self.canvas_size)

    def mark_composite_dirty(self):
        """Mark the composited image cache as dirty."""
        canvas = self.canvas
        self.dirty = True

    def compose(self):
        """
        Ensure that self.image reflects current baseCanvas + drawingLayer.
        This is used for exporting/copying, not for on-screen painting.
        """
        canvas = self.canvas
        if self.dirty:
            self.recompose()
            self.dirty = False

    def ensure_layers(self):
        """Ensure baseCanvas, drawingLayer, and image are allocated to current canvas size."""
        canvas = self.canvas
        sz = self.canvas_size
        if sz.width() <= 0 or sz.height() <= 0:
            return

        if self.base is None or self.base.size() != sz:
            self.base = QImage(sz, QImage.Format_RGB32)
            self.base.fill(Qt.white)
            self.mark_composite_dirty()

        if self.drawing is None or self.drawing.size() != sz:
            self.drawing = QImage(sz, QImage.Format_ARGB32_Premultiplied)
            self.drawing.fill(Qt.transparent)
            self.mark_composite_dirty()

        if self.image.size() != sz:
            self.image = QImage(sz, QImage.Format_RGB32)
            self.image.fill(Qt.white)
            self.mark_composite_dirty()

    def rescale_base_from_source(self):
        """Rebuild baseCanvas from sourceImageOriginal to fit current canvas, preserving aspect ratio."""
        canvas = self.canvas
        self.ensure_layers()
        self.base.fill(Qt.white)
        self.base_rect = QRect()
        if self.source_image is None or self.source_image.isNull():
            self.mark_composite_dirty()
            return

        canvas_size = self.canvas_size
        src = self.source_image
        scaled_size = src.size().scaled(canvas_size, Qt.KeepAspectRatio)
        x = (canvas_size.width() - scaled_size.width()) // 2
        y = (canvas_size.height() - scaled_size.height()) // 2
        self.base_rect = QRect(x, y, scaled_size.width(), scaled_size.height())

        p = QPainter(self.base)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(self.base_rect, src)
        p.end()
        self.mark_composite_dirty()

    def recompose(self):
        """Compose final canvas image from baseCanvas + drawingLayer."""
        canvas = self.canvas
        self.ensure_layers()
        self.image.fill(Qt.white)
        p = QPainter(self.image)
        p.drawImage(QPoint(0, 0), self.base)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.drawImage(QPoint(0, 0), self.drawing)
        p.end()
        self.original_image = self.image

    def open(self, path):
        """
        Open the image

        :param path: Path to image
        """
        canvas = self.canvas
        img = QImage(path)
        if img.isNull():
            QMessageBox.information(canvas, "Image Loader", "Cannot load file.")
            return
        self.set_image(img, fit_canvas_to_image=True)

    def restore(self, path):
        """
        Load a flat image from file as current source.
        This is used for session restore; it does not enforce canvas resize now.

        :param path: Path to image
        """
        canvas = self.canvas
        img = QImage(path)
        if img.isNull():
            return
        self.source_image = QImage(img)
        if self.canvas_size.width() > 0 and self.canvas_size.height() > 0:
            self.ensure_layers()
            self.rescale_base_from_source()
            self.drawing.fill(Qt.transparent)
            self.mark_composite_dirty()
        else:
            pass

    def set_image(self, image, fit_canvas_to_image: bool = False):
        """
        Set image (as new original source)

        :param image: Image
        :param fit_canvas_to_image: True = set canvas size to image size (custom)
        """
        canvas = self.canvas
        if image.isNull():
            return
        canvas.text.cancel(canvas)
        canvas.history.push()
        self.source_image = QImage(image)
        if fit_canvas_to_image:
            w, h = image.width(), image.height()
            canvas.tool.settings.change_canvas_size(f"{w}x{h}")
        # Replacing the source must rebuild layers even when the new image has
        # the same size and change_canvas_size does not trigger a resize.
        self.ensure_layers()
        self.rescale_base_from_source()
        self.drawing.fill(Qt.transparent)
        self.mark_composite_dirty()
        canvas.update()

    def scale_to_fit(self, image):
        """
        Backward-compatibility wrapper. Uses layered model now.

        :param image: Image
        """
        canvas = self.canvas
        self.set_image(image, fit_canvas_to_image=False)

    def clear(self):
        """Clear the image (both background and drawing layer)"""
        canvas = self.canvas
        canvas.text.cancel(canvas)
        self.ensure_layers()
        self.source_image = None
        self.base.fill(Qt.white)
        self.drawing.fill(Qt.transparent)
        self.mark_composite_dirty()
        canvas.update()

    def handle_canvas_resized(self, old_size: QSize, new_size: QSize):
        """
        Apply buffer updates when the logical canvas size changes.

        :param old_size: Previous canvas size
        :param new_size: New canvas size
        """
        canvas = self.canvas
        self.ensure_layers()

        if self.pending_resize is not None:
            new_base = self.pending_resize.get('base')
            new_draw = self.pending_resize.get('draw')

            # Reset layers to new canvas size
            self.base = QImage(new_size, QImage.Format_RGB32)
            self.base.fill(Qt.white)
            self.drawing = QImage(new_size, QImage.Format_ARGB32_Premultiplied)
            self.drawing.fill(Qt.transparent)

            if new_base is not None:
                if new_base.size() == new_size:
                    self.base = QImage(new_base)
                else:
                    bx = (new_size.width() - new_base.width()) // 2
                    by = (new_size.height() - new_base.height()) // 2
                    p = QPainter(self.base)
                    p.drawImage(QPoint(max(0, bx), max(0, by)), new_base)
                    p.end()

            if new_draw is not None:
                if new_draw.size() == new_size:
                    self.drawing = QImage(new_draw)
                else:
                    dx = (new_size.width() - new_draw.width()) // 2
                    dy = (new_size.height() - new_draw.height()) // 2
                    p = QPainter(self.drawing)
                    p.drawImage(QPoint(max(0, dx), max(0, dy)), new_draw)
                    p.end()

            self.pending_resize = None
            self.base_rect = QRect(0, 0, self.base.width(), self.base.height())
            self.mark_composite_dirty()
        else:
            # Rebuild background from original source
            self.rescale_base_from_source()

            # Scale drawing content to new canvas size if previous canvas was valid
            if old_size.isValid() and (old_size.width() > 0 and old_size.height() > 0) and \
                    (self.drawing is not None) and (self.drawing.size() != new_size):
                self.drawing = self.drawing.scaled(new_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self.mark_composite_dirty()

        canvas.update()

