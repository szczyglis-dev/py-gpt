#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.20 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint, QSize, QEvent
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMenuBar,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QScrollArea,
    QToolButton,
    QPushButton,
    QWidget,
    QFrame,
    QStyle,
    QLabel,
)

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
        dialog.disable_geometry_store = False
        dialog.id = id
        dialog.shared_id = self.id

        source = ImageLabel(dialog, self.path)
        source.setVisible(False)
        pixmap = ImageLabel(dialog, self.path)
        pixmap.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))
        pixmap.setAlignment(Qt.AlignCenter)

        # scrollable container for pixmap
        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(pixmap)

        row = QHBoxLayout()
        row.addWidget(scroll)

        layout = QVBoxLayout()
        # remove extra outer margins to bring the toolbar closer to the top/menu bar
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # full-width toolbar frame; icons cluster inside stays compact on the left
        toolbar = dialog.setup_toolbar()
        layout.addWidget(toolbar)
        # image area
        layout.addLayout(row)
        # bottom status bar
        statusbar = dialog.setup_statusbar()
        layout.addWidget(statusbar)

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

        # toolbar icons
        self._icon_prev = QIcon(":/icons/back.svg")
        self._icon_next = QIcon(":/icons/forward.svg")
        self._icon_copy = QIcon(":/icons/copy.svg")
        self._icon_fullscreen = QIcon(":/icons/fullscreen.svg")

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

        # buttons map to keep enabled state in sync with actions
        self._tb_btns = {}

        # status bar widgets and metadata
        self.status_bar = None
        self.lbl_index = None
        self.lbl_resolution = None
        self.lbl_zoom = None
        self.lbl_extra = None

        self._meta_index = 0           # 1-based index of file in dir
        self._meta_total = 0           # total files in dir
        self._meta_img_size = QSize()  # original image size
        self._meta_file_size = ""      # formatted file size string

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
                    # update status bar to reflect new zoom and display size
                    self._refresh_statusbar()
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

    def setup_toolbar(self) -> QFrame:
        """
        Setup top toolbar.
        Full-width frame (Expanding), with a fixed-size icons strip on the left that does not stretch.
        """
        bar = QFrame(self)
        bar.setObjectName("image_viewer_toolbar")
        bar.setFrameShape(QFrame.NoFrame)
        bar.setMinimumHeight(35)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # full width, fixed height

        # scoped minimal style for icon-only QPushButtons
        bar.setStyleSheet(
            """
            #image_viewer_toolbar {
                border: none;
            }
            #image_viewer_toolbar QPushButton {
                border: none;
                padding: 0;
            }
            #image_viewer_toolbar QPushButton:disabled {
                opacity: 0.5;
            }
            """
        )

        # main container layout that fills the width
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # a compact, non-expanding strip that holds the icons
        strip = QWidget(bar)
        strip.setObjectName("image_viewer_toolbar_strip")
        strip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        strip_lay = QHBoxLayout(strip)
        strip_lay.setContentsMargins(6, 6, 6, 6)
        strip_lay.setSpacing(6)

        # DPI-aware icon and button sizes; explicit fixed size prevents vertical squashing
        pm = self.style().pixelMetric(QStyle.PM_ToolBarIconSize)
        if not isinstance(pm, int) or pm <= 0:
            pm = self.style().pixelMetric(QStyle.PM_SmallIconSize)
            if not isinstance(pm, int) or pm <= 0:
                pm = 20
        # reduce icon height by ~5px (and width to keep square) as requested
        icon_px = max(16, pm - 5)
        btn_px = max(29, icon_px + 10)  # keep compact square buttons; min reduced by 5px
        icon_size = QSize(icon_px, icon_px)

        def bind_button_to_action(btn: QPushButton, action: QAction):
            """Keep button in sync with the given action."""
            btn.setIcon(action.icon())
            btn.setToolTip(action.toolTip())
            btn.setEnabled(action.isEnabled())
            action.changed.connect(lambda: (
                btn.setIcon(action.icon()),
                btn.setToolTip(action.toolTip()),
                btn.setEnabled(action.isEnabled())
            ))
            btn.clicked.connect(action.trigger)

        def mk_btn(key: str, icon: QIcon, tooltip: str) -> QPushButton:
            """Create a fixed-size square button with icon-only look."""
            action = QAction(icon, "", self)
            action.setToolTip(tooltip)
            self.actions[key] = action

            btn = QPushButton(strip)
            btn.setObjectName("ivtb")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setFlat(True)
            btn.setText("")
            btn.setIcon(icon)
            btn.setIconSize(icon_size)
            btn.setFixedSize(btn_px, btn_px)

            bind_button_to_action(btn, action)
            self._tb_btns[key] = btn

            strip_lay.addWidget(btn)
            return btn

        def add_sep():
            sep = QFrame(strip)
            sep.setFrameShape(QFrame.VLine)
            sep.setFrameShadow(QFrame.Sunken)
            sep.setFixedHeight(btn_px - 4)
            strip_lay.addWidget(sep)

        # prev
        mk_btn("tb_prev", self._icon_prev, "Previous image")
        self.actions["tb_prev"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").prev_by_id(self.id)
        )

        # next
        mk_btn("tb_next", self._icon_next, "Next image")
        self.actions["tb_next"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").next_by_id(self.id)
        )

        add_sep()

        # open in directory
        mk_btn("tb_open_dir", self._icon_folder, "Open in directory")
        self.actions["tb_open_dir"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").open_dir_by_id(self.id)
        )

        # save as...
        mk_btn("tb_save_as", self._icon_save, "Save as...")
        self.actions["tb_save_as"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").save_by_id(self.id)
        )

        # copy
        mk_btn("tb_copy", self._icon_copy, "Copy to clipboard")
        self.actions["tb_copy"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").copy_by_id(self.id)
        )

        add_sep()

        # fullscreen
        mk_btn("tb_fullscreen", self._icon_fullscreen, "Toggle fullscreen")
        self.actions["tb_fullscreen"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").toggle_fullscreen_by_id(self.id)
        )

        # initial enabled state; actual state adjusted on image load
        for k in ("tb_prev", "tb_next", "tb_open_dir", "tb_save_as", "tb_copy", "tb_fullscreen"):
            if k in self.actions:
                self.actions[k].setEnabled(k == "tb_fullscreen")

        # compose: icons strip on the left, stretch fills the rest so frame spans full width
        lay.addWidget(strip)
        lay.addStretch(1)

        return bar

    def setup_statusbar(self) -> QFrame:
        """
        Setup bottom status bar with four columns:
        1) file index in directory (e.g., 1/13)
        2) displayed size (e.g., 1280x720 px)
        3) current zoom in percent
        4) original image resolution and file size on the right
        """
        bar = QFrame(self)
        bar.setObjectName("image_viewer_statusbar")
        bar.setFrameShape(QFrame.NoFrame)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar.setStyleSheet("""
            #image_viewer_statusbar {
                border: none;
            }
            #image_viewer_statusbar QLabel {
                color: #686868;
                font-size: 12px;
                padding: 4px 8px;
            }
        """)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.lbl_index = QLabel("-", bar)
        self.lbl_resolution = QLabel("-", bar)
        self.lbl_zoom = QLabel("-", bar)
        self.lbl_extra = QLabel("-", bar)

        # make columns distribute evenly; order updated to show current (displayed) on the left,
        # and original with file size on the right: index | displayed | zoom | original (+ size)
        for w in (self.lbl_index, self.lbl_extra, self.lbl_zoom, self.lbl_resolution):
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay.addWidget(self.lbl_index, 1, Qt.AlignLeft)
        lay.addWidget(self.lbl_extra, 1, Qt.AlignLeft)
        lay.addWidget(self.lbl_zoom, 1, Qt.AlignCenter)
        lay.addWidget(self.lbl_resolution, 1, Qt.AlignRight)

        self.status_bar = bar
        self._refresh_statusbar()
        return bar

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
                self.scroll_area.setWidgetResizable(False)
                self.pixmap.setScaledContents(True)
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
            tentative = self._zoom_factor * step
            tentative = max(self._min_zoom, min(self._max_zoom, tentative))
            tentative = self._clamp_factor_by_size(tentative)

            if abs(tentative - self._zoom_factor) < 1e-9:
                event.accept()
                return True

            vp_pos = self._event_pos(event)
            hbar = self.scroll_area.horizontalScrollBar()
            vbar = self.scroll_area.verticalScrollBar()

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

        if factor <= 1.0:
            return factor

        dw = iw * factor
        dh = ih * factor

        scale = 1.0

        total = dw * dh
        if total > self._max_total_pixels:
            from math import sqrt
            scale = min(scale, sqrt(self._max_total_pixels / float(total)))

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
        """
        if not self._has_image():
            return

        src = self.source.pixmap()
        iw = max(1, src.width())
        ih = max(1, src.height())

        new_w = max(1, int(round(iw * factor)))
        new_h = max(1, int(round(ih * factor)))

        guarded_factor = self._clamp_factor_by_size(factor)
        if abs(guarded_factor - factor) > 1e-9:
            new_w = max(1, int(round(iw * guarded_factor)))
            new_h = max(1, int(round(ih * guarded_factor)))
            self._zoom_factor = guarded_factor

        if self._zoom_mode == 'manual':
            if self.pixmap.pixmap() is None or self.pixmap.pixmap().cacheKey() != src.cacheKey():
                self.pixmap.setPixmap(src)
            self.pixmap.setScaledContents(True)
            self.pixmap.resize(new_w, new_h)
        else:
            scaled = src.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.pixmap.setScaledContents(False)
            self.pixmap.setPixmap(scaled)
            if self.scroll_area is not None:
                self.scroll_area.setWidgetResizable(True)

        # keep status bar in sync with zoom and current display size
        self._refresh_statusbar()

    def _event_pos(self, event) -> QPoint:
        """
        Extract integer QPoint from mouse/touchpad event position (supports QPointF in 6.9+).
        """
        if hasattr(event, "position"):
            return event.position().toPoint()
        if hasattr(event, "pos"):
            return event.pos()
        return QPoint(0, 0)

    # =========================
    # Status bar helpers
    # =========================

    def set_status_meta(self, index: int = None, total: int = None, img_size: QSize = None, file_size_str: str = None):
        """
        Update persistent metadata shown in status bar (index/total, original image size, file size).
        """
        if index is not None:
            self._meta_index = max(0, int(index))
        if total is not None:
            self._meta_total = max(0, int(total))
        if img_size is not None:
            self._meta_img_size = QSize(max(0, img_size.width()), max(0, img_size.height()))
        if file_size_str is not None:
            self._meta_file_size = file_size_str or ""
        self._refresh_statusbar()

    def _current_zoom_percent(self) -> int:
        """
        Return current zoom in percent, based on mode.
        """
        factor = self._fit_factor if self._zoom_mode == 'fit' else self._zoom_factor
        try:
            return max(1, int(round(factor * 100.0)))
        except Exception:
            return 100

    def _displayed_size(self) -> QSize:
        """
        Return the currently displayed image size in pixels.
        """
        if self._zoom_mode == 'manual' and self.pixmap is not None:
            return QSize(max(0, self.pixmap.width()), max(0, self.pixmap.height()))
        # in fit mode or when using a scaled pixmap
        if self.pixmap is not None and self.pixmap.pixmap() is not None:
            pm = self.pixmap.pixmap()
            return QSize(max(0, pm.width()), max(0, pm.height()))
        return QSize(0, 0)

    def _refresh_statusbar(self):
        """
        Refresh all status bar labels from current metadata and state.
        """
        if self.lbl_index is None:
            return

        # 1) index/total
        if self._meta_index > 0 and self._meta_total > 0:
            self.lbl_index.setText(f"{self._meta_index}/{self._meta_total}")
        else:
            self.lbl_index.setText("-")

        # 2) left: displayed size only
        dsz = self._displayed_size()
        dsz_txt = f"{dsz.width()}x{dsz.height()} px" if dsz.width() > 0 and dsz.height() > 0 else "-"
        self.lbl_extra.setText(dsz_txt)

        # 3) zoom percent (center)
        self.lbl_zoom.setText(f"{self._current_zoom_percent()}%")

        # 4) right: original resolution with file size appended
        if self._meta_img_size.width() > 0 and self._meta_img_size.height() > 0:
            right_txt = f"{self._meta_img_size.width()}x{self._meta_img_size.height()} px"
            if self._meta_file_size:
                right_txt += f" | {self._meta_file_size}"
            self.lbl_resolution.setText(right_txt)
        else:
            self.lbl_resolution.setText("-")