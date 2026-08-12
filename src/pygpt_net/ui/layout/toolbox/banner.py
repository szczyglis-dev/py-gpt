#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 14:30:00                  #
# ================================================== #

import os
import webbrowser
from typing import Dict, List, Optional, Any

from PySide6.QtCore import QSize, Qt, QTimer, Slot
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import QLabel, QWidget


class Banner:
    """Toolbox banner UI wrapper."""

    WIDTH = 256
    HEIGHT = 54

    def __init__(self, window=None):
        self.window = window

    def setup(self) -> QWidget:
        widget = BannerWidget(
            width=self.WIDTH,
            height=self.HEIGHT,
            default_path=self.window.core.banners.get_default_path(),
            parent=self.window,
        )
        self.window.ui.nodes["toolbox.banner"] = widget
        self.window.core.banners.loaded.connect(widget.set_items)
        return widget


class BannerWidget(QLabel):
    """Clickable banner label with timed rotation and animated GIF support."""

    def __init__(self, width: int, height: int, default_path: str, parent=None):
        super().__init__(parent)
        self.banner_width = width
        self.banner_height = height
        self.default_path = default_path
        self.items: List[Dict[str, Any]] = []
        self.current_index = 0
        self.current_url = ""
        self._movie: Optional[QMovie] = None

        self.setFixedSize(width, height)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { background-color: #000000; border: none; }")
        self.setText("")

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next)

        # The default image is visible immediately while update/banner network
        # checks run in the background.
        self._show_default()

    @Slot(object)
    def set_items(self, items: List[Dict[str, Any]]):
        self.timer.stop()
        self.items = list(items or [])
        self.current_index = 0

        if not self.items:
            self._show_default()
            return
        self._show_current()

    def _show_current(self):
        if not self.items:
            self._show_default()
            return

        if self.current_index >= len(self.items):
            self.current_index = 0

        item = self.items[self.current_index]
        self.current_url = str(item.get("url") or "")
        self.setToolTip(str(item.get("tooltip") or ""))
        if self.current_url:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.unsetCursor()

        self._show_image(item.get("path"))

        try:
            duration_ms = int(float(item.get("duration", 30)) * 1000)
        except (TypeError, ValueError):
            duration_ms = 30000
        self.timer.start(max(1000, duration_ms))

    def _next(self):
        if not self.items:
            return
        self.current_index = (self.current_index + 1) % len(self.items)
        self._show_current()

    def _show_default(self):
        self.timer.stop()
        self.current_url = ""
        self.setToolTip("")
        self.unsetCursor()
        self._show_image(self.default_path if os.path.isfile(self.default_path) else None)

    def _show_image(self, path: Optional[str]):
        self._stop_movie()
        self.clear()

        if not path or not os.path.isfile(path):
            # The QLabel stylesheet supplies the required black fallback.
            return

        if path.lower().endswith(".gif"):
            movie = QMovie(path)
            if movie.isValid():
                movie.setCacheMode(QMovie.CacheAll)
                movie.setScaledSize(QSize(self.banner_width, self.banner_height))
                self._movie = movie
                self.setMovie(movie)
                movie.start()
                return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        pixmap = pixmap.scaled(
            self.banner_width,
            self.banner_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(pixmap)

    def _stop_movie(self):
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.current_url:
            webbrowser.open(self.current_url, new=2)
            event.accept()
            return
        super().mousePressEvent(event)
