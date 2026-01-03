#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint, QSize, QEvent
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QVBoxLayout, QHBoxLayout, QSizePolicy, QScrollArea

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.image.display import ImageLabel
from pygpt_net.utils import trans


class DialogSpawner:
    def __init__(self, window=None):
        """
        Image viewer dialog spawner

        :param window: Window instance
        """
        self.window = window
        self.path = None
        self.id = 'image_preview'

    def setup(self, id: str = None) -> BaseDialog:
        """
        Setup image viewer dialog

        :param id: dialog id
        :return: BaseDialog instance
        """
        dialog = ImageViewerDialog(self.window, self.id)
        dialog.disable_geometry_store = True  # disable geometry store
        dialog.id = id

        source = ImageLabel(dialog, self.path)
        source.setVisible(False)
        pixmap = ImageLabel(dialog, self.path)
        pixmap.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))

        # scrollable container for pixmap
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(pixmap)

        row = QHBoxLayout()
        row.addWidget(scroll)

        layout = QVBoxLayout()
        layout.addLayout(row)

        dialog.append_layout(layout)
        dialog.source = source
        dialog.pixmap = pixmap
        dialog.scroll_area = scroll

        # install event filter for wheel zoom and panning and cursor changes
        dialog.scroll_area.viewport().installEventFilter(dialog)

        return dialog


class ImageViewerDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Image viewer dialog

        :param window: main window
        :param id: info window id
        """
        super(ImageViewerDialog, self).__init__(window, id)
        self.window = window
        self.id = id
        self.disable_geometry_store = False
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}
        self.source = None
        self.pixmap = None
        self.scroll_area = None

        # cache for image change / resize handling
        self._last_src_key = 0
        self._last_target_size = None

        # icons
        self._icon_add = QIcon(":/icons/add.svg")
        self._icon_folder = QIcon(":/icons/folder.svg")
        self._icon_save = QIcon(":/icons/save.svg")
        self._icon_logout = QIcon(":/icons/logout.svg")

        # zoom / pan state
        self._zoom_mode = 'fit'  # 'fit' or 'manual'
        self._zoom_factor = 1.0  # current manual factor (image space)
        self._fit_factor = 1.0   # computed on-the-fly for fit mode
        self._min_zoom = 0.05
        self._max_zoom = 16.0
        self._zoom_step = 1.25
        self._drag_active = False
        self._drag_last_pos = QPoint()

        # performance guards to prevent extremely huge widget sizes
        self._max_widget_dim = 32768          # max single dimension (px) for the view widget
        self._max_total_pixels = 80_000_000   # max total pixels of the view widget (about 80MP)

    def append_layout(self, layout):
        """
        Update layout

        :param layout: layout
        """
        layout.setMenuBar(self.setup_menu())
        self.setLayout(layout)

    def resizeEvent(self, event):
        """
        Resize event to adjust the pixmap on window resizing

        :param event: resize event
        """
        src = self.source.pixmap() if self.source is not None else None
        if src and not src.isNull() and self.pixmap is not None:
            key = src.cacheKey()
            # reset to fit mode on new image
            if key != self._last_src_key:
                self._zoom_mode = 'fit'
                self._zoom_factor = 1.0
                if self.scroll_area is not None:
                    self.scroll_area.setWidgetResizable(True)
                # ensure no distortion in fit mode
                if self.pixmap is not None:
                    self.pixmap.setScaledContents(False)

            if self._zoom_mode == 'fit':
                target_size = self._viewport_size()
                if key != self._last_src_key or target_size != self._last_target_size:
                    # scale to viewport while keeping aspect ratio, smooth transform
                    scaled = src.scaled(
                        target_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.pixmap.setPixmap(scaled)
                    self._fit_factor = self._compute_fit_factor(src.size(), target_size)
                    self._last_src_key = key
                    self._last_target_size = target_size
        super(ImageViewerDialog, self).resizeEvent(event)

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        self.menu_bar = QMenuBar(self)
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))

        self.actions["new"] = QAction(self._icon_add, trans("action.new"), self)
        self.actions["new"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").new()
        )

        self.actions["open"] = QAction(self._icon_folder, trans("action.open"), self)
        self.actions["open"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").open_file(self.id, auto_close=True)
        )

        self.actions["open_new"] = QAction(self._icon_folder, trans("action.open_new_window"), self)
        self.actions["open_new"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").open_file(self.id, auto_close=False)
        )

        self.actions["save_as"] = QAction(self._icon_save, trans("action.save_as"), self)
        self.actions["save_as"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").save_by_id(self.id)
        )

        self.actions["exit"] = QAction(self._icon_logout, trans("menu.file.exit"), self)
        self.actions["exit"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").close_preview(self.id)
        )

        self.file_menu.addAction(self.actions["new"])
        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["open_new"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])

        return self.menu_bar

    # =========================
    # Zoom / pan implementation
    # =========================

    def eventFilter(self, obj, event):
        """
        Handle wheel zoom, panning and cursor changes on the scroll area viewport.
        """
        if self.scroll_area is None or obj is not self.scroll_area.viewport():
            return super(ImageViewerDialog, self).eventFilter(obj, event)

        et = event.type()

        # Always show grab cursor when mouse is over the image area
        if et == QEvent.Enter:
            if self._has_image():
                self.scroll_area.viewport().setCursor(Qt.OpenHandCursor)
            return False

        if et == QEvent.Leave:
            self.scroll_area.viewport().unsetCursor()
            return False

        if et == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton and self._can_drag():
                self._drag_active = True
                self._drag_last_pos = self._event_pos(event)
                self.scroll_area.viewport().setCursor(Qt.ClosedHandCursor)
                event.accept()
                return True
            return False

        if et == QEvent.MouseMove:
            if self._drag_active:
                pos = self._event_pos(event)
                delta = pos - self._drag_last_pos
                self._drag_last_pos = pos
                # move scrollbars opposite to mouse movement
                hbar = self.scroll_area.horizontalScrollBar()
                vbar = self.scroll_area.verticalScrollBar()
                hbar.setValue(hbar.value() - delta.x())
                vbar.setValue(vbar.value() - delta.y())
                event.accept()
                return True
            return False

        if et == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton and self._drag_active:
                self._drag_active = False
                # back to grab cursor
                if self._has_image():
                    self.scroll_area.viewport().setCursor(Qt.OpenHandCursor)
                event.accept()
                return True
            return False

        if et == QEvent.Wheel:
            # zoom in/out with mouse wheel
            if not self._has_image():
                return False

            # start manual zoom from current fit factor if needed
            if self._zoom_mode == 'fit':
                self._fit_factor = self._compute_fit_factor(
                    self.source.pixmap().size(),
                    self._viewport_size()
                )
                self._zoom_factor = self._fit_factor
                self._zoom_mode = 'manual'
                # switch to manual rendering path: original pixmap + scaled contents
                self.scroll_area.setWidgetResizable(False)
                self.pixmap.setScaledContents(True)
                # ensure we display original image for better performance (no giant intermediate pixmaps)
                self.pixmap.setPixmap(self.source.pixmap())

            old_w = max(1, self.pixmap.width())
            old_h = max(1, self.pixmap.height())

            angle = 0
            try:
                angle = event.angleDelta().y()
                if angle == 0:
                    angle = event.angleDelta().x()
            except Exception:
                pass

            if angle == 0:
                return False

            step = self._zoom_step if angle > 0 else (1.0 / self._zoom_step)
            # compute tentative new factor and clamp by hard min/max and size guards
            tentative = self._zoom_factor * step
            tentative = max(self._min_zoom, min(self._max_zoom, tentative))
            # apply size-based guards to avoid extremely huge widget sizes
            tentative = self._clamp_factor_by_size(tentative)

            if abs(tentative - self._zoom_factor) < 1e-9:
                event.accept()
                return True

            vp_pos = self._event_pos(event)
            hbar = self.scroll_area.horizontalScrollBar()
            vbar = self.scroll_area.verticalScrollBar()

            # position in content coords before zoom (keep point under cursor stable)
            content_x = hbar.value() + vp_pos.x()
            content_y = vbar.value() + vp_pos.y()
            rx = content_x / float(old_w)
            ry = content_y / float(old_h)

            self._zoom_factor = tentative
            self._set_scaled_pixmap_by_factor(self._zoom_factor)

            new_w = max(1, self.pixmap.width())
            new_h = max(1, self.pixmap.height())

            hbar.setValue(int(rx * new_w - vp_pos.x()))
            vbar.setValue(int(ry * new_h - vp_pos.y()))

            event.accept()
            return True

        return super(ImageViewerDialog, self).eventFilter(obj, event)

    def _has_image(self) -> bool:
        """Check if source image is available."""
        return (
            self.source is not None
            and self.source.pixmap() is not None
            and not self.source.pixmap().isNull()
            and self.pixmap is not None
        )

    def _can_drag(self) -> bool:
        """Allow dragging only when image does not fit into the viewport."""
        if not self._has_image():
            return False
        if self._zoom_mode != 'manual':
            return False
        vp = self._viewport_size()
        return self.pixmap.width() > vp.width() or self.pixmap.height() > vp.height()

    def _viewport_size(self) -> QSize:
        """Get current viewport size."""
        if self.scroll_area is not None:
            return self.scroll_area.viewport().size()
        return self.size()

    def _compute_fit_factor(self, img_size: QSize, target: QSize) -> float:
        """Compute factor for fitting image into target size."""
        iw = max(1, img_size.width())
        ih = max(1, img_size.height())
        tw = max(1, target.width())
        th = max(1, target.height())
        return min(tw / float(iw), th / float(ih))

    def _clamp_factor_by_size(self, factor: float) -> float:
        """
        Clamp zoom factor to avoid creating extremely large widget sizes.
        This keeps interactivity smooth by limiting max resulting dimensions and total pixels.
        """
        src = self.source.pixmap()
        if not src or src.isNull():
            return factor

        iw = max(1, src.width())
        ih = max(1, src.height())

        # only guard when zooming in; zooming out should not be limited by these caps
        if factor <= 1.0:
            return factor

        # desired size
        dw = iw * factor
        dh = ih * factor

        scale = 1.0

        # total pixel cap
        total = dw * dh
        if total > self._max_total_pixels:
            from math import sqrt
            scale = min(scale, sqrt(self._max_total_pixels / float(total)))

        # dimension caps
        if dw * scale > self._max_widget_dim:
            scale = min(scale, self._max_widget_dim / float(dw))
        if dh * scale > self._max_widget_dim:
            scale = min(scale, self._max_widget_dim / float(dh))

        if scale < 1.0:
            return max(self._min_zoom, factor * scale)
        return factor

    def _set_scaled_pixmap_by_factor(self, factor: float):
        """
        Scale and display the image using provided factor relative to the original image.
        In manual mode this avoids allocating giant intermediate QPixmaps by:
        - drawing the original pixmap;
        - enabling scaled contents;
        - resizing the label to the required size.
        """
        if not self._has_image():
            return

        src = self.source.pixmap()
        iw = max(1, src.width())
        ih = max(1, src.height())

        # target size based on factor (KeepAspectRatio preserved by proportional math)
        new_w = max(1, int(round(iw * factor)))
        new_h = max(1, int(round(ih * factor)))

        # enforce guards once more to be safe
        guarded_factor = self._clamp_factor_by_size(factor)
        if abs(guarded_factor - factor) > 1e-9:
            new_w = max(1, int(round(iw * guarded_factor)))
            new_h = max(1, int(round(ih * guarded_factor)))
            self._zoom_factor = guarded_factor  # keep internal factor in sync

        if self._zoom_mode == 'manual':
            # ensure manual path uses original pixmap and scaled contents
            if self.pixmap.pixmap() is None or self.pixmap.pixmap().cacheKey() != src.cacheKey():
                self.pixmap.setPixmap(src)
            self.pixmap.setScaledContents(True)
            self.pixmap.resize(new_w, new_h)
        else:
            # fallback (not expected here): keep classic high-quality scaling
            scaled = src.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.pixmap.setScaledContents(False)
            self.pixmap.setPixmap(scaled)
            if self.scroll_area is not None:
                self.scroll_area.setWidgetResizable(True)

    def _event_pos(self, event) -> QPoint:
        """
        Extract integer QPoint from mouse/touchpad event position (supports QPointF in 6.9+).
        """
        if hasattr(event, "position"):
            return event.position().toPoint()
        if hasattr(event, "pos"):
            return event.pos()
        return QPoint(0, 0)