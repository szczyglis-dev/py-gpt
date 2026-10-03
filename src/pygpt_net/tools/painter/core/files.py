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

import datetime
import os

from PySide6.QtCore import Qt, QPoint, QSaveFile, QIODevice
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QFileDialog


class Files:
    """Painter files operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas

    def save(self, path: str, include_drawing: bool = False) -> bool:
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
        canvas = self.canvas
        if not path:
            return False

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass

        if canvas.document.source_image is not None and not canvas.document.source_image.isNull():
            if not include_drawing:
                return canvas.files.save_atomic(canvas.document.source_image, path)

            src = QImage(canvas.document.source_image)
            if canvas.document.drawing is None or canvas.document.drawing.isNull():
                return canvas.files.save_atomic(src, path)

            if canvas.document.base_rect.isNull() or canvas.document.base_rect.width() <= 0 or canvas.document.base_rect.height() <= 0:
                return canvas.files.save_atomic(src, path)

            overlay_canvas_roi = canvas.document.drawing.copy(canvas.document.base_rect)
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

            return canvas.files.save_atomic(result, path)

        canvas.document.compose()
        return canvas.files.save_atomic(canvas.document.image, path)

    def save_atomic(self, img: QImage, path: str, fmt: str = None, quality: int = -1) -> bool:
        """
        Save an image atomically using QSaveFile. Returns True on success.

        :param img: Image
        :param path: Path to save
        :param fmt: Format (e.g. 'PNG', 'JPEG'); if None, inferred from file extension
        :param quality: Quality (0-100) or -1 for default
        :return: True on success
        """
        canvas = self.canvas
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

    def open_dialog(self):
        """Open the image"""
        canvas = self.canvas
        path, _ = QFileDialog.getOpenFileName(
            canvas,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg)",
        )
        if path:
            canvas.document.open(path)

    def save_dialog(self):
        """Save image to file"""
        canvas = self.canvas
        canvas.document.compose()
        name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
        path, _ = QFileDialog.getSaveFileName(
            canvas,
            "Save Image",
            name,
            "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ",
        )
        if path:
            canvas.document.image.save(path)

