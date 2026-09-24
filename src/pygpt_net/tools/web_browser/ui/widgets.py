#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 02:05:00                  #
# ================================================== #

from PySide6.QtCore import Qt, Slot, QUrl, QObject, Signal, QSize, QPoint, QTimer, QEvent
from PySide6.QtGui import QIcon, QAction, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QSizePolicy,
    QScrollArea, QMenu, QFrame, QPlainTextEdit, QStackedLayout, QLabel,
)
from PySide6.QtWebEngineCore import QWebEnginePage

from pygpt_net.ui.widget.textarea.html import HtmlOutput
from pygpt_net.utils import trans


class ToolWidget:
    """A UI owner for the single persistent browser runtime surface."""

    def __init__(self, window=None, tool=None, surface_kind="tab"):
        self.window = window
        self.tool = tool
        self.surface_kind = surface_kind
        self.output = None
        self.tab = None
        self.nav_bar = None
        self.nav_layout = None
        self.address_bar = None
        self.btn_back = None
        self.btn_next = None
        self.btn_reload = None
        self.btn_go = None
        self.scroll = None
        self._layout = None
        self.viewport_badge = None
        self.plugin_hint = None
        self._plugin_action = None
        self._viewport_filter = None
        self._viewport_sync_timer = None
        self._columns_splitter = None
        self._app_ready_connected = False

    def on_open(self):
        self.tool.attach_surface(self)
        self._sync_from_runtime()
        self.request_viewport_sync(immediate=True)

    def on_close(self):
        self.tool.detach_surface(self)

    def on_delete(self):
        self._disconnect_viewport_hooks()
        self.tool.detach_surface(self)

    def _take_surface(self):
        if self.scroll is None:
            return None
        try:
            return self.scroll.takeWidget()
        except Exception:
            return None

    def attach_runtime_surface(self, surface):
        self.output = surface
        if self.scroll is not None:
            old = self.scroll.takeWidget()
            if old is not None and old is not surface:
                old.setParent(None)
            self.scroll.setWidget(surface)
            surface.show()
            self.request_viewport_sync(immediate=True)

    def set_tab(self, tab):
        self.tab = tab
        if self.output is not None:
            self.output.set_tab(tab)
        self.request_viewport_sync(immediate=True)

    def setup(self, all: bool = True) -> QVBoxLayout:
        self.nav_bar = QWidget()
        self.nav_layout = QHBoxLayout(self.nav_bar)
        self.nav_layout.setContentsMargins(6, 4, 6, 4)
        self.nav_layout.setSpacing(6)
        self.nav_bar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        icon_size_px = 20
        nav_height = 36
        self.nav_bar.setFixedHeight(nav_height)

        def button(icon, tip):
            btn = QPushButton()
            btn.setToolTip(tip)
            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(icon_size_px, icon_size_px))
            btn.setFixedHeight(nav_height - 8)
            btn.setAutoDefault(False)
            try:
                btn.setDefault(False)
            except Exception:
                pass
            return btn

        self.btn_back = button(":/icons/back.svg", trans("ui.back", domain="plugin.canvas_web"))
        self.btn_next = button(":/icons/forward.svg", trans("ui.next", domain="plugin.canvas_web"))
        self.btn_reload = button(":/icons/reload.svg", trans("ui.reload", domain="plugin.canvas_web"))
        self.btn_go = button(":/icons/redo.svg", trans("ui.open_url", domain="plugin.canvas_web"))
        self.address_bar = AddressLineEdit(on_return_callback=self._on_address_enter)
        self.address_bar.setPlaceholderText(trans("ui.address_placeholder", domain="plugin.canvas_web"))
        self.address_bar.setFixedHeight(nav_height - 8)
        self.address_bar.returnPressed.connect(self._on_address_enter)

        self.btn_back.clicked.connect(lambda: self.tool.runtime_call("canvas_prev", {"__ui": True}))
        self.btn_next.clicked.connect(lambda: self.tool.runtime_call("canvas_next", {"__ui": True}))
        self.btn_reload.clicked.connect(lambda: self.tool.runtime_call("canvas_reload", {"__ui": True}))
        self.btn_go.clicked.connect(self._on_address_enter)

        self.nav_layout.addWidget(self.btn_back)
        self.nav_layout.addWidget(self.btn_next)
        self.nav_layout.addWidget(self.btn_reload)
        self.nav_layout.addWidget(self.address_bar, 1)
        self.nav_layout.addWidget(self.btn_go)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.viewport_badge = QLabel("", self.scroll.viewport())
        self.viewport_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.viewport_badge.setStyleSheet(
            "QLabel {"
            " background: rgba(24, 24, 24, 175);"
            " color: white;"
            " border-radius: 5px;"
            " padding: 3px 7px;"
            " font-size: 11px;"
            "}"
        )
        self.viewport_badge.setText("0 × 0")
        self.viewport_badge.adjustSize()
        self.viewport_badge.show()

        self.plugin_hint = QLabel(
            trans("ui.enable_hint", domain="plugin.canvas_web"),
            self.scroll.viewport(),
        )
        self.plugin_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.plugin_hint.setStyleSheet(
            "QLabel {"
            " background: rgba(24, 24, 24, 175);"
            " color: white;"
            " border-radius: 5px;"
            " padding: 3px 7px;"
            " font-size: 11px;"
            "}"
        )
        self.plugin_hint.adjustSize()
        self._update_plugin_hint()
        self._connect_plugin_hint_hook()

        self._viewport_filter = ViewportEventFilter(self.scroll)
        self._viewport_filter.changed.connect(self._on_viewport_geometry_changed)
        self.scroll.viewport().installEventFilter(self._viewport_filter)

        self._viewport_sync_timer = QTimer(self.scroll)
        self._viewport_sync_timer.setSingleShot(True)
        self._viewport_sync_timer.timeout.connect(self._sync_runtime_viewport)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.nav_bar, 0)
        layout.addWidget(self.scroll, 1)
        self._layout = layout
        self._connect_viewport_hooks()
        if self.surface_kind == "tab":
            self.tool.attach_surface(self)
        QTimer.singleShot(0, lambda: self.request_viewport_sync(immediate=True))
        QTimer.singleShot(80, lambda: self.request_viewport_sync(immediate=True))
        return layout

    @Slot(str)
    def open_url(self, url: str):
        self.tool.runtime_call("canvas_open", {"url": url, "__ui": True})

    def _on_address_enter(self):
        if self.address_bar is None:
            return
        text = self.address_bar.text().strip()
        if text:
            self.tool.runtime_call("canvas_open", {"url": text, "__ui": True})

    def _sync_from_runtime(self):
        state = self.tool.current_state()
        if self.address_bar is not None:
            self.address_bar.setText(state.get("url", ""))
        if self.btn_back is not None:
            self.btn_back.setEnabled(bool(state.get("can_go_back")))
        if self.btn_next is not None:
            self.btn_next.setEnabled(bool(state.get("can_go_forward")))
        if self.btn_reload is not None:
            self.btn_reload.setEnabled(True)

    def on_runtime_state(self, state: dict):
        self._sync_from_runtime()
        self._update_viewport_badge(state)
        self._update_plugin_hint()
        # The application has one canonical Canvas tab, but its title
        # may still follow the currently rendered document.  This is only a
        # label update; it must never be used as tab identity.
        title = state.get("title") or ""
        if self.tab is not None and title and title != "about:blank":
            try:
                self.window.controller.ui.tabs.update_title_by_tab(self.tab, title)
            except Exception:
                pass

    def _connect_viewport_hooks(self):
        """Observe all geometry changes that can alter the visible Canvas area."""
        if self.window is None:
            return
        splitter = self.window.ui.splitters.get("columns")
        if splitter is not None and splitter is not self._columns_splitter:
            if self._columns_splitter is not None:
                try:
                    self._columns_splitter.splitterMoved.disconnect(self._on_columns_splitter_moved)
                except Exception:
                    pass
            self._columns_splitter = splitter
            try:
                splitter.splitterMoved.connect(self._on_columns_splitter_moved)
            except Exception:
                pass
        if not self._app_ready_connected:
            try:
                self.window.appReady.connect(self._on_app_ready)
                self._app_ready_connected = True
            except Exception:
                pass

    def _disconnect_viewport_hooks(self):
        if self._plugin_action is not None:
            try:
                self._plugin_action.toggled.disconnect(self._on_canvas_plugin_toggled)
            except Exception:
                pass
            self._plugin_action = None
        if self.scroll is not None and self._viewport_filter is not None:
            try:
                self.scroll.viewport().removeEventFilter(self._viewport_filter)
            except Exception:
                pass
        if self._columns_splitter is not None:
            try:
                self._columns_splitter.splitterMoved.disconnect(self._on_columns_splitter_moved)
            except Exception:
                pass
            self._columns_splitter = None
        if self.window is not None and self._app_ready_connected:
            try:
                self.window.appReady.disconnect(self._on_app_ready)
            except Exception:
                pass
            self._app_ready_connected = False

    def _on_app_ready(self):
        self._connect_plugin_hint_hook()
        self._update_plugin_hint()
        self.request_viewport_sync(immediate=True)

    def _on_columns_splitter_moved(self, _pos, _index):
        # Let QSplitter finish assigning child geometries before reading the
        # QScrollArea viewport. Coalesce the high-frequency drag events.
        self.request_viewport_sync(immediate=False)

    def _on_viewport_geometry_changed(self):
        self._position_viewport_overlays()
        self.request_viewport_sync(immediate=False)

    def request_viewport_sync(self, immediate: bool = False):
        """Schedule runtime viewport synchronization with the Canvas column."""
        if self._viewport_sync_timer is None:
            return
        self._connect_viewport_hooks()
        self._viewport_sync_timer.start(0 if immediate else 30)

    def _column_visible(self) -> bool:
        """Return False only when the Canvas output column is fully collapsed."""
        if self.tab is None:
            return False
        try:
            column_idx = int(self.tab.column_idx)
        except Exception:
            return False
        splitter = self.window.ui.splitters.get("columns") if self.window is not None else None
        if splitter is None or splitter.count() <= column_idx:
            return True
        try:
            sizes = splitter.sizes()
            return column_idx < len(sizes) and int(sizes[column_idx]) > 0
        except Exception:
            return True

    def _sync_runtime_viewport(self):
        if self.tool is None or self.scroll is None or self.tab is None:
            return
        visible = self._column_visible()
        if not visible:
            self.tool.request_viewport_policy(visible=False, delay=0)
            return

        viewport = self.scroll.viewport()
        width = int(viewport.width())
        height = int(viewport.height())
        if width <= 0 or height <= 0:
            return
        self.tool.request_viewport_policy(width, height, visible=True, delay=0)

    def _update_viewport_badge(self, state: dict):
        if self.viewport_badge is None:
            return
        width = int(state.get("width") or 0)
        height = int(state.get("height") or 0)
        self.viewport_badge.setText(f"{width} × {height}")
        self.viewport_badge.adjustSize()
        self._position_viewport_overlays()

    def _is_canvas_plugin_enabled(self) -> bool:
        if self.window is None:
            return False
        try:
            return bool(self.window.controller.plugins.is_enabled("canvas_web"))
        except Exception:
            pass
        try:
            plugin = self.window.core.plugins.get("canvas_web")
            return bool(plugin is not None and getattr(plugin, "enabled", False))
        except Exception:
            return False

    def _update_plugin_hint(self):
        if self.plugin_hint is None:
            return
        self.plugin_hint.setVisible(not self._is_canvas_plugin_enabled())
        self._position_viewport_overlays()

    def _connect_plugin_hint_hook(self):
        if self.window is None or self._plugin_action is not None:
            return
        try:
            action = self.window.ui.menu.get("plugins", {}).get("canvas_web")
        except Exception:
            action = None
        if action is None:
            return
        try:
            action.toggled.connect(self._on_canvas_plugin_toggled)
            self._plugin_action = action
        except Exception:
            self._plugin_action = None

    def _on_canvas_plugin_toggled(self, _checked=False):
        # Controller state is updated by the action handler in the same event
        # cycle. Defer one turn so the hint always reflects the final state.
        QTimer.singleShot(0, self._update_plugin_hint)

    def _position_viewport_overlays(self):
        if self.scroll is None:
            return
        viewport = self.scroll.viewport()
        margin = 8
        if self.viewport_badge is not None:
            x = max(margin, viewport.width() - self.viewport_badge.width() - margin)
            y = max(margin, viewport.height() - self.viewport_badge.height() - margin)
            self.viewport_badge.move(x, y)
            self.viewport_badge.raise_()
        if self.plugin_hint is not None:
            y = max(margin, viewport.height() - self.plugin_hint.height() - margin)
            self.plugin_hint.move(margin, y)
            self.plugin_hint.raise_()


class BrowserPage(QWebEnginePage):
    """QWebEngine page that forwards console/errors to the shared browser runtime."""

    def __init__(self, tool=None, parent=None):
        super().__init__(parent)
        self.tool = tool

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        if self.tool is not None:
            if self.tool.handle_annotation_console(message):
                return
            self.tool.append_qt_console(level, message, line_number, source_id)
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class BrowserOutput(HtmlOutput):
    """QWebEngine backend used when Playwright sandbox mode is disabled."""

    def __init__(self, window=None, tool=None):
        self.tool = tool
        super().__init__(window)
        self.window = window
        self.setPage(BrowserPage(tool=tool, parent=self))
        if tool is not None:
            self.signals.save_as.connect(tool.handle_save_as)
        if window is not None:
            self.signals.audio_read.connect(window.controller.chat.render.handle_audio_read)

    def _detach_gl_event_filter(self):
        """Detach WebEngine's transient GL child without logging stale Qt wrappers.

        QWebEngine may destroy/recreate its internal render widget while the
        persistent canvas surface is reparented.  In that case the Python wrapper
        can still be truthy even though the underlying C++ QWidget is already
        gone.  Treat that as normal teardown rather than an application error.
        """
        glwidget = getattr(self, "_glwidget", None)
        installed = bool(getattr(self, "_glwidget_filter_installed", False))
        if glwidget is not None and installed:
            try:
                glwidget.removeEventFilter(self)
            except RuntimeError as exc:
                if "already deleted" not in str(exc).lower():
                    try:
                        self._on_delete_failed(exc)
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    self._on_delete_failed(exc)
                except Exception:
                    pass
        self._glwidget = None
        self._glwidget_filter_installed = False

    def on_page_loaded(self, success):
        if self.tool is not None:
            self.tool.on_qt_load_finished(bool(success))

    def on_context_menu(self, position):
        menu = QMenu(self)
        selected = self.page().selectedText() if self.page().hasSelection() else ""
        if selected:
            copy_action = QAction(QIcon(":/icons/copy.svg"), trans("ui.copy", domain="plugin.canvas_web"), self)
            copy_action.triggered.connect(self.copy_selected_text)
            menu.addAction(copy_action)
            annotate = QAction(trans("ui.annotate_selection", domain="plugin.canvas_web"), self)
            annotate.triggered.connect(lambda: self.tool.annotate_selection(selected, position, backend="qt"))
            menu.addAction(annotate)
        else:
            annotate = QAction(trans("ui.annotate_element", domain="plugin.canvas_web"), self)
            annotate.triggered.connect(lambda: self.tool.annotate_at(position.x(), position.y(), backend="qt"))
            menu.addAction(annotate)
            select_all = QAction(trans("ui.select_all", domain="plugin.canvas_web"), self)
            select_all.triggered.connect(self.select_all_text)
            menu.addAction(select_all)
        menu.addSeparator()
        show_source = QAction(trans("ui.show_source", domain="plugin.canvas_web"), self)
        show_source.triggered.connect(self.tool.show_source)
        menu.addAction(show_source)
        menu.addSeparator()
        back = QAction(trans("ui.back", domain="plugin.canvas_web"), self)
        back.triggered.connect(lambda: self.tool.runtime_call("canvas_prev", {"__ui": True}))
        menu.addAction(back)
        forward = QAction(trans("ui.next", domain="plugin.canvas_web"), self)
        forward.triggered.connect(lambda: self.tool.runtime_call("canvas_next", {"__ui": True}))
        menu.addAction(forward)
        reload_action = QAction(trans("ui.reload", domain="plugin.canvas_web"), self)
        reload_action.triggered.connect(lambda: self.tool.runtime_call("canvas_reload", {"__ui": True}))
        menu.addAction(reload_action)
        menu.exec_(self.mapToGlobal(position))


class SandboxView(QWidget):
    """Remote framebuffer-like frontend for the headless Playwright page."""

    def __init__(self, tool=None, parent=None):
        super().__init__(parent)
        self.tool = tool
        self._pixmap = QPixmap()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_frame(self, data: bytes):
        pix = QPixmap()
        if data and pix.loadFromData(data):
            self._pixmap = pix
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._pixmap.isNull():
            painter.drawPixmap(self.rect(), self._pixmap)
        else:
            painter.fillRect(self.rect(), self.palette().base())
        if self.tool is not None:
            x, y = self.tool.cursor_x, self.tool.cursor_y
            pen = QPen(self.palette().highlight().color())
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawEllipse(QPoint(int(x), int(y)), 7, 7)
            painter.drawLine(int(x) - 11, int(y), int(x) + 11, int(y))
            painter.drawLine(int(x), int(y) - 11, int(x), int(y) + 11)
            painter.drawText(int(x) + 10, int(y) - 10, "AI")

    def mouseMoveEvent(self, event):
        if self.tool is not None:
            p = event.position()
            self.tool.user_playwright_action("hover", {"x": int(p.x()), "y": int(p.y())})
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        if self.tool is not None:
            p = event.position()
            if event.button() == Qt.RightButton:
                self.tool.user_playwright_action("hover", {"x": int(p.x()), "y": int(p.y())})
                event.accept()
                return
            buttons = {Qt.LeftButton: "left", Qt.MiddleButton: "middle"}
            self.tool.user_playwright_action("mouse_down", {
                "x": int(p.x()), "y": int(p.y()), "button": buttons.get(event.button(), "left")})
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            event.accept()
            return
        if self.tool is not None:
            p = event.position()
            buttons = {Qt.LeftButton: "left", Qt.MiddleButton: "middle"}
            self.tool.user_playwright_action("mouse_up", {
                "x": int(p.x()), "y": int(p.y()), "button": buttons.get(event.button(), "left")})
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.tool is not None and event.button() == Qt.LeftButton:
            p = event.position()
            self.tool.user_playwright_action("click", {"x": int(p.x()), "y": int(p.y()), "count": 2})
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if self.tool is not None:
            delta = event.angleDelta()
            self.tool.user_playwright_action("scroll", {"dx": -delta.x(), "dy": -delta.y()})
        event.accept()

    def keyPressEvent(self, event):
        if self.tool is not None:
            special_keys = {
                Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape, Qt.Key_Tab,
                Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right,
                Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End,
                Qt.Key_PageUp, Qt.Key_PageDown,
            }
            text = event.text()
            has_command_modifier = bool(event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
            if event.key() in special_keys or has_command_modifier or not text:
                key = self.tool.qt_key_to_playwright(event)
                if key:
                    self.tool.user_playwright_action("key", {"key": key})
            else:
                self.tool.user_playwright_action("type_raw", {"text": text})
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        p = event.pos()
        # Keep the menu instant. Selection detection is performed inside the
        # page when the action is invoked, so opening RMB never waits on
        # synchronous Playwright evaluation.
        annotate_selection = QAction(trans("ui.annotate_selection", domain="plugin.canvas_web"), self)
        annotate_selection.triggered.connect(lambda: self.tool.annotate_selection("", p, backend="playwright"))
        menu.addAction(annotate_selection)
        annotate = QAction(trans("ui.annotate_element", domain="plugin.canvas_web"), self)
        annotate.triggered.connect(lambda: self.tool.annotate_at(p.x(), p.y(), backend="playwright"))
        menu.addAction(annotate)
        menu.addSeparator()
        show_source = QAction(trans("ui.show_source", domain="plugin.canvas_web"), self)
        show_source.triggered.connect(self.tool.show_source)
        menu.addAction(show_source)
        menu.exec_(event.globalPos())


class SourceEditor(QPlainTextEdit):
    """Plain-text HTML source editor for the current browser document."""

    def __init__(self, tool=None, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabChangesFocus(False)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if menu.actions():
            menu.addSeparator()
        back = QAction(trans("ui.back_to_canvas", domain="plugin.canvas_web"), self)
        back.triggered.connect(self.tool.show_canvas)
        menu.addAction(back)
        menu.exec_(event.globalPos())


class BrowserViewport(QWidget):
    """Persistent browser viewport with rendered and editable-source modes."""

    SOURCE_DEBOUNCE_MS = 450

    def __init__(self, window=None, tool=None):
        super().__init__()
        self.window = window
        self.tool = tool
        self.tab = None
        self.web = BrowserOutput(window, tool)
        self.sandbox = SandboxView(tool)
        self.source = SourceEditor(tool, self)
        self._mode = "qt"
        self._source_visible = False
        self._source_loading = False
        self._source_base_url = ""
        self._source_timer = QTimer(self)
        self._source_timer.setSingleShot(True)
        self._source_timer.setInterval(self.SOURCE_DEBOUNCE_MS)
        self._source_timer.timeout.connect(self._apply_source)
        self.source.textChanged.connect(self._on_source_changed)

        # A real stack is more reliable than hide/show for QWebEngineView. In
        # particular it avoids Chromium keeping its compositor surface above the
        # source editor on some Linux/Wayland/X11 combinations.
        self.layout = QStackedLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.web)
        self.layout.addWidget(self.sandbox)
        self.layout.addWidget(self.source)
        self.layout.setCurrentWidget(self.web)
        self.set_resolution(1280, 800)

    def set_tab(self, tab):
        self.tab = tab
        self.web.set_tab(tab)

    def set_mode(self, mode: str):
        self._mode = mode
        if self._source_visible:
            self.layout.setCurrentWidget(self.source)
            return
        self.layout.setCurrentWidget(self.sandbox if mode == "playwright" else self.web)

    def show_source(self, html: str, base_url: str = ""):
        self._source_timer.stop()
        self._source_loading = True
        try:
            self.source.setPlainText(str(html or ""))
            self.source.document().setModified(False)
            self._source_base_url = str(base_url or "")
            self._source_visible = True
            self.layout.setCurrentWidget(self.source)
            self.source.setFocus(Qt.OtherFocusReason)
        finally:
            self._source_loading = False

    def show_canvas(self):
        # Flush the last pending edit before revealing the rendered result.
        if self._source_visible and self._source_timer.isActive():
            self._source_timer.stop()
            self._apply_source()
        self._source_visible = False
        self.set_mode(self._mode)
        self.active_view().setFocus(Qt.OtherFocusReason)

    def _on_source_changed(self):
        if self._source_loading or not self._source_visible:
            return
        self._source_timer.start()

    def _apply_source(self):
        if self._source_loading or not self._source_visible or self.tool is None:
            return
        html = self.source.toPlainText()
        try:
            self.tool.apply_source_html(html, self._source_base_url)
            self.source.document().setModified(False)
        except Exception as exc:
            try:
                self.tool._append_console("source", "error", str(exc))
            except Exception:
                pass

    def set_resolution(self, width: int, height: int):
        # Model/API resolution limits are enforced by WebBrowser._set_resolution.
        # The UI fitter may legitimately need a narrower pane while the user is
        # dragging the split-screen handle, so the QWidget itself must accept the
        # real available size all the way down to 1 px.
        width = max(1, int(width))
        height = max(1, int(height))
        self.setFixedSize(width, height)
        self.web.setFixedSize(width, height)
        self.sandbox.setFixedSize(width, height)
        self.source.setFixedSize(width, height)

    def active_view(self):
        if self._source_visible:
            return self.source
        return self.sandbox if self._mode == "playwright" else self.web

    def shutdown(self):
        self._source_timer.stop()
        try:
            self.web.on_delete()
        except Exception:
            pass


class ViewportEventFilter(QObject):
    """Emit a compact signal whenever the QScrollArea viewport geometry changes."""

    changed = Signal()

    def eventFilter(self, source, event):
        if event.type() in (QEvent.Resize, QEvent.Show):
            self.changed.emit()
        return super().eventFilter(source, event)


class AddressLineEdit(QLineEdit):
    def __init__(self, on_return_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_return_callback = on_return_callback

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if callable(self._on_return_callback):
                self._on_return_callback()
            event.accept()
            return
        super().keyPressEvent(event)


class ToolSignals(QObject):
    url = Signal(str)
    closed = Signal()
    state = Signal(dict)
