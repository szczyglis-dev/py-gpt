#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 20:00:00                  #
# ================================================== #

import datetime
import os
from collections import deque

from PySide6.QtCore import Qt, QPoint, QRect, QSize, QSaveFile, QIODevice, QTimer
from PySide6.QtGui import QImage, QPainter, QPen, QAction, QIcon, QColor, QCursor
from PySide6.QtWidgets import QMenu, QWidget, QFileDialog, QMessageBox, QApplication, QAbstractScrollArea

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class PainterWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window

        # Final composited image (canvas-sized). Kept for API compatibility.
        self.image = QImage(self.size(), QImage.Format_RGB32)

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
        self.lastPoint = QPoint()
        self._pen = QPen(self.brushColor, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

        # Crop tool state
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
        self._act_fit = QAction(QIcon(":/icons/resize.svg"), trans('painter.btn.fit') if trans('painter.btn.fit') else "Fit", self)
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

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    # ---------- Layer & composition helpers ----------

    def _ensure_layers(self):
        """Ensure baseCanvas, drawingLayer, and image are allocated to current canvas size."""
        sz = self.size()
        if sz.width() <= 0 or sz.height() <= 0:
            return

        if self.baseCanvas is None or self.baseCanvas.size() != sz:
            self.baseCanvas = QImage(sz, QImage.Format_RGB32)
            self.baseCanvas.fill(Qt.white)

        if self.drawingLayer is None or self.drawingLayer.size() != sz:
            self.drawingLayer = QImage(sz, QImage.Format_ARGB32_Premultiplied)
            self.drawingLayer.fill(Qt.transparent)

        if self.image.size() != sz:
            self.image = QImage(sz, QImage.Format_RGB32)
            self.image.fill(Qt.white)

    def _rescale_base_from_source(self):
        """
        Rebuild baseCanvas from sourceImageOriginal to fit current canvas, preserving aspect ratio.
        """
        self._ensure_layers()
        self.baseCanvas.fill(Qt.white)
        self.baseTargetRect = QRect()
        if self.sourceImageOriginal is None or self.sourceImageOriginal.isNull():
            return

        canvas_size = self.size()
        src = self.sourceImageOriginal
        # Compute scaled size that fits within the canvas (max width/height)
        scaled_size = src.size().scaled(canvas_size, Qt.KeepAspectRatio)
        # Center the image within the canvas
        x = (canvas_size.width() - scaled_size.width()) // 2
        y = (canvas_size.height() - scaled_size.height()) // 2
        self.baseTargetRect = QRect(x, y, scaled_size.width(), scaled_size.height())

        p = QPainter(self.baseCanvas)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(self.baseTargetRect, src)
        p.end()

    def _recompose(self):
        """Compose final canvas image from baseCanvas + drawingLayer."""
        self._ensure_layers()
        self.image.fill(Qt.white)
        p = QPainter(self.image)
        # draw background
        p.drawImage(QPoint(0, 0), self.baseCanvas)
        # draw drawing layer
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
            'size': QSize(self.width(), self.height()),
            'baseRect': QRect(self.baseTargetRect),
        }
        return state

    def _apply_state(self, state):
        """Apply a snapshot (used by undo/redo)."""
        if not state:
            return
        self._ignoreResizeOnce = True
        target_size = state['size']

        # Set canvas size if needed
        if target_size != self.size():
            self.setFixedSize(target_size)

        # Apply layers and image
        self.image = QImage(state['image']) if state['image'] is not None else QImage(self.size(), QImage.Format_RGB32)
        if self.image.size() != self.size():
            self.image = self.image.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        if state['base'] is not None:
            self.baseCanvas = QImage(state['base'])
        else:
            self.baseCanvas = QImage(self.size(), QImage.Format_RGB32)
            self.baseCanvas.fill(Qt.white)

        if state['draw'] is not None:
            self.drawingLayer = QImage(state['draw'])
        else:
            self.drawingLayer = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
            self.drawingLayer.fill(Qt.transparent)

        self.sourceImageOriginal = QImage(state['src']) if state['src'] is not None else None
        self.baseTargetRect = QRect(state['baseRect']) if state['baseRect'] is not None else QRect()

        self._ignoreResizeOnce = False
        self.update()

    def _is_fit_available(self) -> bool:
        """Return True if there are letterbox margins that can be trimmed."""
        # Ensure composition is current
        self._recompose()

        # If we have a valid target rect that does not cover the whole canvas, fit is available
        if self.baseTargetRect.isValid() and not self.baseTargetRect.isNull():
            if self.baseTargetRect.width() < self.width() or self.baseTargetRect.height() < self.height():
                return True

        # Fallback: detect non-white content bounds on the composited image
        bounds = self._detect_nonwhite_bounds(self.image)
        if bounds is not None:
            # Fit is useful only if bounds are strictly smaller than canvas
            return bounds.width() < self.width() or bounds.height() < self.height()
        return False

    def action_fit(self):
        """Trim white letterbox margins and resize canvas to the scaled image area. Undo-safe."""
        if not self._is_fit_available():
            return

        self.saveForUndo()
        self._ensure_layers()
        self._recompose()

        # Prefer exact baseTargetRect if available
        fit_rect = None
        if self.baseTargetRect.isValid() and not self.baseTargetRect.isNull():
            # Clip to canvas just in case
            canvas_rect = QRect(0, 0, self.width(), self.height())
            fit_rect = self.baseTargetRect.intersected(canvas_rect)

        # Fallback to content bounds if baseTargetRect is not usable
        if fit_rect is None or fit_rect.isNull() or fit_rect.width() <= 0 or fit_rect.height() <= 0:
            fit_rect = self._detect_nonwhite_bounds(self.image)
            if fit_rect is None or fit_rect.isNull() or fit_rect.width() <= 0 or fit_rect.height() <= 0:
                # Nothing to do
                return

        # If already tight, do nothing
        if fit_rect.width() == self.width() and fit_rect.height() == self.height():
            return

        # Prepare exact pixels to apply after the canvas resize (pixel-perfect, no rescale)
        new_base = self.baseCanvas.copy(fit_rect)
        new_draw = self.drawingLayer.copy(fit_rect)

        self._pendingResizeApply = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }

        # Keep original source as-is: mapped area equals the full image, quality is preserved.
        # After resize, resizeEvent will set baseTargetRect to the full canvas.
        self.window.controller.painter.common.change_canvas_size(f"{fit_rect.width()}x{fit_rect.height()}")
        self.update()

    def _detect_nonwhite_bounds(self, img: QImage, threshold: int = 250) -> QRect | None:
        """
        Detect tight bounding rect of non-white content in a composited image.
        A pixel is considered background if all channels >= threshold.
        Returns None if no non-white content is found.
        """
        if img is None or img.isNull():
            return None

        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return None

        def is_bg(px: QColor) -> bool:
            return px.red() >= threshold and px.green() >= threshold and px.blue() >= threshold

        # Scan from four sides until content is found; early exits minimize work on large images.
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

        # Validate bounds
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
                # paste should create custom canvas with image size
                self.set_image(image, fit_canvas_to_image=True)

    def handle_copy(self):
        """Handle clipboard copy"""
        # ensure composited image is up-to-date
        self._recompose()
        clipboard = QApplication.clipboard()
        clipboard.setImage(self.image)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: Event
        """
        self._act_undo.setEnabled(self.has_undo())
        self._act_redo.setEnabled(self.has_redo())
        self._act_fit.setEnabled(self._is_fit_available())

        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        self._act_paste.setEnabled(bool(mime_data.hasImage()))

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
        # ensure composited image is up-to-date
        self._recompose()
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
        # Treat opening as loading a new original; resize canvas to image size (custom)
        self.set_image(img, fit_canvas_to_image=True)

    def load_flat_image(self, path):
        """
        Load a flat image from file as current source.
        This is used for session restore; it does not enforce canvas resize now.
        """
        img = QImage(path)
        if img.isNull():
            return
        # Do not change canvas size here; setup() will follow with change_canvas_size().
        self.sourceImageOriginal = QImage(img)
        # Rebuild layers for current canvas (if any size already set)
        if self.width() > 0 and self.height() > 0:
            self._ensure_layers()
            self._rescale_base_from_source()
            self.drawingLayer.fill(Qt.transparent)
            self._recompose()
        else:
            # defer until resize arrives
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
            # set custom canvas size to image size
            w, h = image.width(), image.height()
            self.window.controller.painter.common.change_canvas_size(f"{w}x{h}")
        else:
            # just rebuild within current canvas
            self._ensure_layers()
            self._rescale_base_from_source()
            self.drawingLayer.fill(Qt.transparent)
            self._recompose()
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
        # Ensure layers up-to-date before snapshot
        self._ensure_layers()
        self._recompose()
        self.undoStack.append(self._snapshot_state())
        self.redoStack.clear()

    def undo(self):
        """Undo the last action"""
        if self.undoStack:
            current = self._snapshot_state()
            self.redoStack.append(current)
            state = self.undoStack.pop()
            self._apply_state(state)
            # Keep size combo in sync with restored canvas and source (handles sticky custom)
            if self.window and hasattr(self.window, "controller"):
                self.window.controller.painter.common.sync_canvas_combo_from_widget()

    def redo(self):
        """Redo the last undo action"""
        if self.redoStack:
            current = self._snapshot_state()
            self.undoStack.append(current)
            state = self.redoStack.pop()
            self._apply_state(state)
            # Keep size combo in sync with restored canvas and source (handles sticky custom)
            if self.window and hasattr(self.window, "controller"):
                self.window.controller.painter.common.sync_canvas_combo_from_widget()

    def has_undo(self) -> bool:
        """Check if undo is available"""
        return bool(self.undoStack)

    def has_redo(self) -> bool:
        """Check if redo is available"""
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

        # Ensure parent directory exists
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            # Directory creation failure is not fatal for cases when dir already exists
            pass

        # If we have the original (or cropped original), use it
        if self.sourceImageOriginal is not None and not self.sourceImageOriginal.isNull():
            if not include_drawing:
                return self._save_image_atomic(self.sourceImageOriginal, path)

            # Composite drawing onto the original at original resolution
            src = QImage(self.sourceImageOriginal)
            if self.drawingLayer is None or self.drawingLayer.isNull():
                return self._save_image_atomic(src, path)

            # If we know where the original was drawn on the canvas, map strokes accordingly
            if self.baseTargetRect.isNull() or self.baseTargetRect.width() <= 0 or self.baseTargetRect.height() <= 0:
                # Unknown mapping; save the pure original to avoid wrong scaling
                return self._save_image_atomic(src, path)

            # Extract strokes over the image area, scale them to original resolution, and blend
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

        # No original available: save the current composited canvas as a safe fallback
        self._recompose()
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

        # Infer a format from file extension; default to PNG
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
        # cursor hint
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
        self._recompose()
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
        # Always stop autoscroll when finishing the crop
        self._stop_autoscroll()
        if not self.cropping or self._selectionRect.isNull() or self._selectionRect.width() <= 1 or self._selectionRect.height() <= 1:
            self.cancel_crop()
            return

        self._ensure_layers()
        sel = self._selectionRect.normalized()
        # Keep previous state for undo
        # saveForUndo called on mousePress at crop start

        # Crop base and drawing layers to selection
        new_base = self.baseCanvas.copy(sel)
        new_draw = self.drawingLayer.copy(sel)

        # Prepare to apply exact cropped pixels after resize event
        self._pendingResizeApply = {
            'base': QImage(new_base),
            'draw': QImage(new_draw),
        }

        # Update original source to cropped region for future high-quality resizes
        if self.sourceImageOriginal is not None and not self.baseTargetRect.isNull():
            inter = sel.intersected(self.baseTargetRect)
            if inter.isValid() and not inter.isNull():
                # Map intersection rect to original source coordinates
                sx_ratio = self.sourceImageOriginal.width() / self.baseTargetRect.width()
                sy_ratio = self.sourceImageOriginal.height() / self.baseTargetRect.height()

                dx = inter.x() - self.baseTargetRect.x()
                dy = inter.y() - self.baseTargetRect.y()

                sx = max(0, int(dx * sx_ratio))
                sy = max(0, int(dy * sy_ratio))
                sw = max(1, int(inter.width() * sx_ratio))
                sh = max(1, int(inter.height() * sy_ratio))
                # Clip
                if sx + sw > self.sourceImageOriginal.width():
                    sw = self.sourceImageOriginal.width() - sx
                if sy + sh > self.sourceImageOriginal.height():
                    sh = self.sourceImageOriginal.height() - sy
                if sw > 0 and sh > 0:
                    self.sourceImageOriginal = self.sourceImageOriginal.copy(sx, sy, sw, sh)
                else:
                    self.sourceImageOriginal = None
            else:
                # Selection outside of image; keep no source
                self.sourceImageOriginal = None
        else:
            # No original source, nothing to update
            pass

        # Resize canvas to selection size; resizeEvent will apply _pendingResizeApply
        self.cropping = False
        self._selecting = False
        self._selectionRect = QRect()
        self.unsetCursor()

        # Perform canvas resize (custom)
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

        # Cursor position relative to viewport
        global_pos = QCursor.pos()
        pos_vp = vp.mapFromGlobal(global_pos)

        margin = self._autoScrollMargin
        dx = 0
        dy = 0

        # Horizontal autoscroll
        if pos_vp.x() < margin:
            dx = -self._calc_scroll_step(pos_vp.x(), margin)
        elif pos_vp.x() > vp.width() - margin:
            dist = max(0, vp.width() - pos_vp.x())
            dx = self._calc_scroll_step(dist, margin)

        # Vertical autoscroll
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

        # Update current selection end using the real pointer position in widget coords.
        if self._selecting:
            pos_widget = self.mapFromGlobal(global_pos)
            cx = min(max(0, pos_widget.x()), max(0, self.width() - 1))
            cy = min(max(0, pos_widget.y()), max(0, self.height() - 1))
            self._selectionRect = QRect(self._selectionStart, QPoint(cx, cy))
            if scrolled or dx != 0 or dy != 0:
                self.update()

    # ---------- Events ----------

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        if event.button() == Qt.LeftButton:
            self._mouseDown = True
            if self.cropping:
                self.saveForUndo()
                self._selecting = True
                self._selectionStart = event.pos()
                self._selectionRect = QRect(self._selectionStart, self._selectionStart)
                self.update()
                # Begin crop drag with mouse grab + autoscroll
                self.grabMouse()
                self._start_autoscroll()
                return

            # painting
            self._ensure_layers()
            self.drawing = True
            self.lastPoint = event.pos()
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
            p.drawPoint(self.lastPoint)
            p.end()
            self._recompose()
            self.update()

    def mouseMoveEvent(self, event):
        """
        Mouse move event

        :param event: Event
        """
        if self.cropping and self._selecting and (event.buttons() & Qt.LeftButton):
            self._selectionRect = QRect(self._selectionStart, event.pos())
            self.update()
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            self._ensure_layers()
            p = QPainter(self.drawingLayer)
            p.setRenderHint(QPainter.Antialiasing, True)
            if self._mode == "erase":
                p.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen(Qt.transparent, self.brushSize, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                p.setPen(pen)
            else:
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
                p.setPen(self._pen)
            p.drawLine(self.lastPoint, event.pos())
            p.end()
            self.lastPoint = event.pos()
            self._recompose()
            self.update()

    def mouseReleaseEvent(self, event):
        """
        Mouse release event

        :param event: Event
        """
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
            # finalize crop with Enter
            if self.cropping and self._selecting:
                self._finalize_crop()
        elif event.key() == Qt.Key_Escape:
            # cancel crop
            if self.cropping:
                self.cancel_crop()

    def paintEvent(self, event):
        """
        Paint event (draw)

        :param event: Event
        """
        # Ensure final composition is valid
        if self.image.size() != self.size():
            self._ensure_layers()
            self._rescale_base_from_source()
            self._recompose()

        p = QPainter(self)
        p.drawImage(self.rect(), self.image, self.image.rect())

        # Draw crop overlay if active
        if self.cropping and not self._selectionRect.isNull():
            sel = self._selectionRect.normalized()
            overlay = QColor(0, 0, 0, 120)
            W, H = self.width(), self.height()

            # left
            if sel.left() > 0:
                p.fillRect(0, 0, sel.left(), H, overlay)
            # right
            if sel.right() < W - 1:
                p.fillRect(sel.right() + 1, 0, W - (sel.right() + 1), H, overlay)
            # top
            if sel.top() > 0:
                p.fillRect(sel.left(), 0, sel.width(), sel.top(), overlay)
            # bottom
            if sel.bottom() < H - 1:
                p.fillRect(sel.left(), sel.bottom() + 1, sel.width(), H - (sel.bottom() + 1), overlay)

            # selection border
            p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
            p.drawRect(sel.adjusted(0, 0, -1, -1))

        p.end()
        self.originalImage = self.image

    def resizeEvent(self, event):
        """
        Update layers on resize

        :param event: Event
        """
        if self._ignoreResizeOnce:
            return super().resizeEvent(event)

        old_size = event.oldSize()
        new_size = event.size()

        # Allocate new layers and recompose
        self._ensure_layers()

        if self._pendingResizeApply is not None:
            # Apply exact cropped pixels to new canvas size; center if differs
            new_base = self._pendingResizeApply.get('base')
            new_draw = self._pendingResizeApply.get('draw')

            # Resize canvas already happened; we need to place these images exactly fitting the canvas size.
            # If sizes match new canvas, copy directly; else center them.
            self.baseCanvas.fill(Qt.white)
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
            # baseTargetRect becomes entire canvas if new_base filled it; otherwise keep unknown
            self.baseTargetRect = QRect(0, 0, self.baseCanvas.width(), self.baseCanvas.height())
        else:
            # Standard path: rebuild base from original source to avoid quality loss
            self._rescale_base_from_source()

            # Scale drawing layer content to new size. This may introduce minor quality loss, acceptable.
            if old_size.isValid() and (old_size.width() > 0 and old_size.height() > 0) and \
                    (self.drawingLayer is not None) and (self.drawingLayer.size() != new_size):
                self.drawingLayer = self.drawingLayer.scaled(new_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        self._recompose()
        self.update()
        super().resizeEvent(event)

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