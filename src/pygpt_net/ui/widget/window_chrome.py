#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.19 22:30:00                  #
# ================================================== #

import os

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QIcon, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSpinBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QScrollBar,
    QSlider,
    QSplitter,
    QTabBar,
    QTextEdit,
    QPushButton,
    QLabel,
    QSizePolicy,
    QWidget,
)


class HoverTintButton(QPushButton):
    """Button that tints only its icon while hovered."""

    def __init__(self, hover_color: str, parent=None):
        super().__init__(parent)
        self._hover_color = QColor(hover_color)
        self._normal_icon = QIcon()
        self._hover_icon = QIcon()
        self._is_hovered = False

    def setIcon(self, icon: QIcon):
        """Keep the original icon and build a runtime-tinted hover variant."""
        self._normal_icon = QIcon(icon)
        self._hover_icon = self._tinted_icon(self._normal_icon)
        super().setIcon(self._hover_icon if self._is_hovered else self._normal_icon)

    def _tinted_icon(self, icon: QIcon) -> QIcon:
        pixmap = icon.pixmap(self.iconSize(), QIcon.Normal, QIcon.Off)
        if pixmap.isNull():
            return QIcon(icon)

        tinted = pixmap.copy()
        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), self._hover_color)
        painter.end()
        return QIcon(tinted)

    def enterEvent(self, event):
        self._is_hovered = True
        if not self._hover_icon.isNull():
            super().setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        if not self._normal_icon.isNull():
            super().setIcon(self._normal_icon)
        super().leaveEvent(event)


class WindowChrome(QObject):
    """Native-like controls and move/resize handling for the frameless main window."""

    RESIZE_MARGIN = 5
    ICON_SIZE = 15
    BUTTON_WIDTH = 34
    BUTTON_HEIGHT = 26

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.menu_bar = None
        self.container = None
        self.profile_label = None
        self.version_label = None
        self.btn_minimize = None
        self.btn_maximize = None
        self.btn_close = None

        # Do NOT install this filter on QApplication. QtWebEngine/PySide6 on
        # Linux can crash natively when a Python event filter sees all app events.
        self._drag_widgets = set()
        self._resize_handles = {}

        self._manual_dragging = False
        self._manual_drag_offset = QPoint()
        self._manual_resize_edges = None
        self._manual_resize_origin = QPoint()
        self._manual_resize_geometry = QRect()
        self._manual_grab_widget = None

    def setup(self):
        """Attach window controls and local move/resize handlers."""
        self.menu_bar = self.window.menuBar()
        self.menu_bar.setNativeMenuBar(False)

        if self.container is None:
            self.container = QWidget(self.menu_bar)
            self.container.setObjectName("windowControls")

            layout = QHBoxLayout(self.container)
            # Keep metadata compact and nudge it slightly below the top edge.
            # The labels use a non-expanding size policy below, so spare menu-bar
            # width never turns into a large gap between profile and version.
            layout.setContentsMargins(0, 5, 0, 0)
            layout.setSpacing(0)

            self.profile_label = self._make_meta_label("windowProfileLabel")
            profile_font = self.profile_label.font()
            profile_font.setBold(True)
            self.profile_label.setFont(profile_font)

            self.version_label = self._make_meta_label("windowVersionLabel")

            self.btn_minimize = self._make_button(
                "windowMinimizeButton",
                "window_minimize.svg",
                lambda checked=False: self.window.showMinimized(),
            )
            self.btn_maximize = self._make_button(
                "windowMaximizeButton",
                "window_maximize.svg",
                self._toggle_maximized,
            )
            self.btn_close = self._make_button(
                "windowCloseButton",
                "window_close.svg",
                lambda checked=False: self.window.close(),
                hover_icon_color="#ffffff",
            )

            layout.addWidget(self.profile_label)
            layout.addSpacing(20)
            layout.addWidget(self.version_label)
            layout.addSpacing(20)
            layout.addWidget(self.btn_minimize)
            layout.addWidget(self.btn_maximize)
            layout.addWidget(self.btn_close)

            self.container.setStyleSheet(
                "QPushButton {"
                "  border: 0;"
                "  border-radius: 0px;"
                "  margin: 0;"
                "  padding: 0;"
                "  background: transparent;"
                "}"
                "QPushButton:hover {"
                "  background: rgba(127, 127, 127, 38);"
                "}"
                "QPushButton:pressed {"
                "  background: rgba(127, 127, 127, 58);"
                "}"
                "QPushButton#windowCloseButton:hover {"
                "  background: #e81123;"
                "}"
                "QPushButton#windowCloseButton:pressed {"
                "  background: #c50f1f;"
                "}"
            )

        self.menu_bar.setCornerWidget(self.container, Qt.TopRightCorner)

        # Local filters only. Never install WindowChrome on QApplication: PyGPT
        # embeds QWebEngineView and a global Python event filter is unsafe there.
        self.window.installEventFilter(self)
        self.menu_bar.installEventFilter(self)
        self._install_drag_filters()
        self._setup_resize_handles()
        self.refresh_metadata()
        self.update_state()
        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        """Refresh locally filtered passive widgets and edge handles."""
        self._install_drag_filters()
        self._position_resize_handles()
        self.refresh_metadata()
        self.update_state()


    def _make_meta_label(self, object_name: str) -> QLabel:
        """Create a compact secondary-text label for the frameless menu bar."""
        label = QLabel(self.container)
        label.setObjectName(object_name)
        label.setProperty('class', 'label-help')
        label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        label.setFixedHeight(self.BUTTON_HEIGHT)
        label.setFocusPolicy(Qt.NoFocus)
        label.setTextInteractionFlags(Qt.NoTextInteraction)
        label.setContentsMargins(0, 0, 0, 0)
        return label

    def refresh_metadata(self):
        """Refresh current profile name and application version in the title bar."""
        if self.profile_label is not None:
            try:
                name = self.window.core.config.profile.get_current_name()
            except (AttributeError, RuntimeError):
                name = ""
            profile_text = str(name or "")
            self.profile_label.setText(profile_text)
            # QMenuBar corner widgets do not always recalculate their width when
            # a child label changes after setup (for example after profile
            # switch/rename). Reserve the exact text width so the right-aligned
            # profile name cannot lose its leading characters.
            self.profile_label.setMinimumWidth(
                self.profile_label.fontMetrics().horizontalAdvance(profile_text) + 2
                if profile_text else 0
            )

        if self.version_label is not None:
            try:
                version = self.window.meta.get("version", "")
            except (AttributeError, RuntimeError):
                version = ""

            version_text = f"v{version}" if version else ""
            self.version_label.setText(version_text)
            self.version_label.setMinimumWidth(
                self.version_label.fontMetrics().horizontalAdvance(version_text) + 2
                if version_text else 0
            )

        if self.container is not None:
            self.profile_label.updateGeometry() if self.profile_label is not None else None
            self.version_label.updateGeometry() if self.version_label is not None else None
            self.container.updateGeometry()
            self.container.adjustSize()
            if self.menu_bar is not None:
                self.menu_bar.updateGeometry()

    def _make_button(
        self,
        object_name: str,
        icon_name: str,
        callback,
        hover_icon_color: str | None = None,
    ) -> QPushButton:
        if hover_icon_color is not None:
            button = HoverTintButton(hover_icon_color, self.container)
        else:
            button = QPushButton(self.container)
        button.setObjectName(object_name)
        button.setFlat(True)
        button.setText("")
        button.setFocusPolicy(Qt.NoFocus)
        button.setCursor(Qt.ArrowCursor)
        button.setFixedSize(self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        button.setIconSize(QSize(self.ICON_SIZE, self.ICON_SIZE))
        button.setIcon(self._icon(icon_name))
        button.clicked.connect(callback)
        return button

    def _icon(self, name: str) -> QIcon:
        path = os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "icons",
            name,
        )
        return QIcon(path)

    def update_state(self):
        """Refresh controls after maximize/fullscreen state changes."""
        if self.container is not None:
            # F11 fullscreen remains completely chrome-free.
            self.container.setVisible(not self.window.isFullScreen())

        if self.btn_maximize is not None:
            if self.window.isMaximized():
                self.btn_maximize.setIcon(self._icon("window_restore.svg"))
            else:
                self.btn_maximize.setIcon(self._icon("window_maximize.svg"))

        resize_visible = (
            self.window.isVisible()
            and not self.window.isFullScreen()
            and not self.window.isMaximized()
            and not self.window.isMinimized()
        )
        for handle in self._resize_handles:
            handle.setVisible(resize_visible)
            if resize_visible:
                handle.raise_()

    def _toggle_maximized(self, checked=False):
        if self.window.isFullScreen():
            return
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()
        QTimer.singleShot(0, self.update_state)

    @staticmethod
    def _event_global_pos(event: QMouseEvent) -> QPoint:
        try:
            return event.globalPosition().toPoint()
        except Exception:
            return event.globalPos()

    def _is_inside_window(self, widget) -> bool:
        if not isinstance(widget, QWidget):
            return False
        try:
            return widget.window() is self.window
        except Exception:
            return False

    @staticmethod
    def _has_webengine_ancestor(widget) -> bool:
        """Keep our Python event filter completely outside QWebEngine widget trees."""
        current = widget
        while isinstance(current, QWidget):
            try:
                class_name = current.metaObject().className()
            except Exception:
                class_name = type(current).__name__
            if "WebEngine" in class_name or "WebView" in class_name:
                return True
            current = current.parentWidget()
        return False

    @staticmethod
    def _is_interactive_ancestor(widget) -> bool:
        interactive = (
            QAbstractButton,
            QAbstractItemView,
            QAbstractScrollArea,
            QAbstractSpinBox,
            QComboBox,
            QLineEdit,
            QMenu,
            QMenuBar,
            QPlainTextEdit,
            QScrollBar,
            QSlider,
            QSplitter,
            QTabBar,
            QTextEdit,
        )
        current = widget
        while isinstance(current, QWidget):
            if isinstance(current, interactive):
                return True
            current = current.parentWidget()
        return False

    def _is_passive_drag_widget(self, widget) -> bool:
        """Return True only for plain, non-interactive background widgets."""
        if not self._is_inside_window(widget):
            return False
        if widget is self.window or widget is self.menu_bar or widget is self.container:
            return False
        if type(widget) not in (QWidget, QFrame):
            return False
        if self._has_webengine_ancestor(widget):
            return False
        if self._is_interactive_ancestor(widget):
            return False
        if widget.property("noWindowDrag"):
            return False
        return True

    def _install_drag_filters(self):
        """Install filters only on passive Qt widgets, never on QApplication/WebEngine."""
        for widget in self.window.findChildren(QWidget):
            if widget in self._drag_widgets:
                continue
            if not self._is_passive_drag_widget(widget):
                continue
            widget.installEventFilter(self)
            self._drag_widgets.add(widget)

    def _setup_resize_handles(self):
        if self._resize_handles:
            return

        cursors = {
            Qt.LeftEdge: Qt.SizeHorCursor,
            Qt.RightEdge: Qt.SizeHorCursor,
            Qt.TopEdge: Qt.SizeVerCursor,
            Qt.BottomEdge: Qt.SizeVerCursor,
            Qt.LeftEdge | Qt.TopEdge: Qt.SizeFDiagCursor,
            Qt.RightEdge | Qt.BottomEdge: Qt.SizeFDiagCursor,
            Qt.RightEdge | Qt.TopEdge: Qt.SizeBDiagCursor,
            Qt.LeftEdge | Qt.BottomEdge: Qt.SizeBDiagCursor,
        }

        for edges, cursor in cursors.items():
            handle = QWidget(self.window)
            handle.setObjectName("windowResizeHandle")
            handle.setMouseTracking(True)
            handle.setCursor(QCursor(cursor))
            handle.setStyleSheet("background: transparent;")
            handle.installEventFilter(self)
            self._resize_handles[handle] = edges

        self._position_resize_handles()

    def _position_resize_handles(self):
        if not self._resize_handles:
            return

        w = max(0, self.window.width())
        h = max(0, self.window.height())
        m = self.RESIZE_MARGIN
        inner_w = max(0, w - 2 * m)
        inner_h = max(0, h - 2 * m)

        geometries = {
            Qt.LeftEdge: QRect(0, m, m, inner_h),
            Qt.RightEdge: QRect(max(0, w - m), m, m, inner_h),
            Qt.TopEdge: QRect(m, 0, inner_w, m),
            Qt.BottomEdge: QRect(m, max(0, h - m), inner_w, m),
            Qt.LeftEdge | Qt.TopEdge: QRect(0, 0, m, m),
            Qt.RightEdge | Qt.TopEdge: QRect(max(0, w - m), 0, m, m),
            Qt.RightEdge | Qt.BottomEdge: QRect(max(0, w - m), max(0, h - m), m, m),
            Qt.LeftEdge | Qt.BottomEdge: QRect(0, max(0, h - m), m, m),
        }

        for handle, edges in self._resize_handles.items():
            handle.setGeometry(geometries[edges])
            handle.raise_()

    def _is_menu_drag_area(self, global_pos: QPoint) -> bool:
        if self.menu_bar is None or not self.menu_bar.isVisible():
            return False
        pos = self.menu_bar.mapFromGlobal(global_pos)
        if not self.menu_bar.rect().contains(pos):
            return False
        if self.menu_bar.actionAt(pos) is not None:
            return False
        if self.container is not None and self.container.isVisible():
            controls_pos = self.container.mapFromGlobal(global_pos)
            if self.container.rect().contains(controls_pos):
                return False
        return True

    def _start_move(self, global_pos: QPoint, source_widget: QWidget) -> bool:
        if self.window.isFullScreen():
            return False

        handle = self.window.windowHandle()
        if handle is not None:
            try:
                if handle.startSystemMove():
                    return True
            except Exception:
                pass

        # Fallback for platforms/window managers without startSystemMove().
        if self.window.isMaximized():
            frame = self.window.frameGeometry()
            normal = self.window.normalGeometry()
            ratio = 0.5
            if frame.width() > 0:
                ratio = (global_pos.x() - frame.left()) / frame.width()
                ratio = max(0.0, min(1.0, ratio))
            self.window.showNormal()
            QTimer.singleShot(0, self.update_state)
            width = normal.width() if normal.width() > 0 else self.window.width()
            x = int(global_pos.x() - width * ratio)
            y = global_pos.y() - min(12, self.menu_bar.height() if self.menu_bar else 12)
            self.window.move(x, y)

        self._manual_dragging = True
        self._manual_drag_offset = global_pos - self.window.frameGeometry().topLeft()
        self._manual_grab_widget = source_widget
        try:
            source_widget.grabMouse()
        except Exception:
            pass
        return True

    def _start_resize(self, edges, global_pos: QPoint, source_widget: QWidget) -> bool:
        if self.window.isFullScreen() or self.window.isMaximized() or self.window.isMinimized():
            return False

        handle = self.window.windowHandle()
        if handle is not None:
            try:
                if handle.startSystemResize(edges):
                    return True
            except Exception:
                pass

        self._manual_resize_edges = edges
        self._manual_resize_origin = global_pos
        self._manual_resize_geometry = self.window.geometry()
        self._manual_grab_widget = source_widget
        try:
            source_widget.grabMouse()
        except Exception:
            pass
        return True

    def _manual_mouse_move(self, global_pos: QPoint) -> bool:
        if self._manual_dragging:
            self.window.move(global_pos - self._manual_drag_offset)
            return True

        if self._manual_resize_edges is not None:
            delta = global_pos - self._manual_resize_origin
            rect = QRect(self._manual_resize_geometry)
            edges = self._manual_resize_edges

            if edges & Qt.LeftEdge:
                rect.setLeft(rect.left() + delta.x())
            if edges & Qt.RightEdge:
                rect.setRight(rect.right() + delta.x())
            if edges & Qt.TopEdge:
                rect.setTop(rect.top() + delta.y())
            if edges & Qt.BottomEdge:
                rect.setBottom(rect.bottom() + delta.y())

            min_w = max(1, self.window.minimumWidth())
            min_h = max(1, self.window.minimumHeight())
            if rect.width() < min_w:
                if edges & Qt.LeftEdge:
                    rect.setLeft(rect.right() - min_w + 1)
                else:
                    rect.setRight(rect.left() + min_w - 1)
            if rect.height() < min_h:
                if edges & Qt.TopEdge:
                    rect.setTop(rect.bottom() - min_h + 1)
                else:
                    rect.setBottom(rect.top() + min_h - 1)

            self.window.setGeometry(rect)
            return True

        return False

    def _stop_manual_operation(self):
        if not self._manual_dragging and self._manual_resize_edges is None:
            return

        self._manual_dragging = False
        self._manual_resize_edges = None
        grab_widget = self._manual_grab_widget
        self._manual_grab_widget = None
        if grab_widget is not None:
            try:
                grab_widget.releaseMouse()
            except Exception:
                pass

    def eventFilter(self, watched, event):
        event_type = event.type()

        if watched is self.window:
            if event_type in (QEvent.Resize, QEvent.Show):
                QTimer.singleShot(0, self._position_resize_handles)
                QTimer.singleShot(0, self.update_state)
            return False

        if event_type not in (
            QEvent.MouseButtonPress,
            QEvent.MouseButtonDblClick,
            QEvent.MouseMove,
            QEvent.MouseButtonRelease,
        ):
            return False
        if not isinstance(event, QMouseEvent):
            return False

        if event_type == QEvent.MouseMove:
            if self._manual_dragging or self._manual_resize_edges is not None:
                return self._manual_mouse_move(self._event_global_pos(event))
            return False

        if event_type == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                self._stop_manual_operation()
            return False

        if event.button() != Qt.LeftButton:
            return False

        global_pos = self._event_global_pos(event)

        if watched in self._resize_handles:
            if event_type == QEvent.MouseButtonPress:
                return self._start_resize(self._resize_handles[watched], global_pos, watched)
            return False

        if watched is self.menu_bar:
            if event_type == QEvent.MouseButtonDblClick and self._is_menu_drag_area(global_pos):
                self._toggle_maximized()
                return True
            if event_type == QEvent.MouseButtonPress and self._is_menu_drag_area(global_pos):
                return self._start_move(global_pos, watched)
            return False

        if watched in self._drag_widgets and event_type == QEvent.MouseButtonPress:
            return self._start_move(global_pos, watched)

        return False
