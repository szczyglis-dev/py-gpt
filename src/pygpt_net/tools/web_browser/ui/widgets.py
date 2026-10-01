#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.29 19:30:00                  #
# ================================================== #

from PySide6.QtCore import Qt, Slot, QUrl, QObject, Signal, QSize, QPoint, QTimer, QEvent
from PySide6.QtGui import QIcon, QAction, QPainter, QPen, QPixmap, QDesktopServices, QShortcut, QKeySequence, QPalette, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QSizePolicy,
    QScrollArea, QMenu, QFrame, QStackedLayout, QLabel, QCompleter,
)
from PySide6.QtWebEngineCore import QWebEnginePage

from pygpt_net.core.text.editor import TextEditor
from pygpt_net.ui.widget.textarea.html import HtmlOutput
from pygpt_net.utils import trans


CANVAS_LOCALE_DOMAIN = "plugin.canvas_web"


class AddressHistoryCompleter(QCompleter):
    """Completer that displays a friendly label but inserts the raw URL."""

    def pathFromIndex(self, index):
        url = index.data(Qt.UserRole)
        if url:
            return str(url)
        return super().pathFromIndex(index)


def add_html_file_actions(menu, tool, parent):
    """Add external-browser and delayed Open/Save HTML actions to Canvas RMB menus."""
    current_url = str(tool.current_url() if tool is not None else "").strip()
    external = QAction(
        QIcon(":/icons/public_filled.svg"),
        trans("web.context_menu.open_browser"),
        parent,
    )
    external.setEnabled(bool(current_url) and current_url != "about:blank")
    external.triggered.connect(
        lambda checked=False, url=current_url: QDesktopServices.openUrl(QUrl(url, QUrl.TolerantMode))
    )
    menu.addAction(external)

    open_html = QAction(
        QIcon(":/icons/folder_open.svg"),
        trans("ui.open_html", domain="plugin.canvas_web"),
        parent,
    )
    open_html.triggered.connect(lambda: QTimer.singleShot(0, tool.open_html_file))
    menu.addAction(open_html)

    save_html = QAction(
        QIcon(":/icons/save.svg"),
        trans("ui.save_html", domain="plugin.canvas_web"),
        parent,
    )
    save_html.triggered.connect(lambda: QTimer.singleShot(0, tool.save_html_file))
    menu.addAction(save_html)


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
        self.address_completer = None
        self.address_history_model = None
        self._address_history_entries = []
        self._address_history_labels = []
        self._address_history_lookup = {}
        self.btn_back = None
        self.btn_next = None
        self.btn_reload = None
        self.btn_home = None
        self.btn_go = None
        self.scroll = None
        self._layout = None
        self.viewport_badge = None
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
        button_size = nav_height - 8
        self.nav_bar.setFixedHeight(nav_height)

        def button(icon):
            btn = QPushButton()
            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(icon_size_px, icon_size_px))
            btn.setFixedSize(button_size, button_size)
            btn.setAutoDefault(False)
            try:
                btn.setDefault(False)
            except Exception:
                pass
            return btn

        self.btn_back = button(":/icons/back.svg")
        self.btn_next = button(":/icons/forward.svg")
        self.btn_reload = button(":/icons/reload.svg")
        self.btn_home = button(":/icons/home.svg")
        self.btn_go = button(":/icons/redo.svg")
        self.tool.add_lang_mapping(self.btn_back, "ui.back", "setToolTip", CANVAS_LOCALE_DOMAIN)
        self.tool.add_lang_mapping(self.btn_next, "ui.next", "setToolTip", CANVAS_LOCALE_DOMAIN)
        self.tool.add_lang_mapping(self.btn_reload, "ui.reload", "setToolTip", CANVAS_LOCALE_DOMAIN)
        self.tool.add_lang_mapping(self.btn_home, "ui.home", "setToolTip", CANVAS_LOCALE_DOMAIN)
        self.tool.add_lang_mapping(self.btn_go, "ui.open_url", "setToolTip", CANVAS_LOCALE_DOMAIN)

        self.address_bar = AddressLineEdit(
            on_return_callback=self._on_address_enter,
            on_reload_callback=lambda: self.tool.runtime_call("canvas_reload", {"__ui": True}),
        )
        self.tool.add_lang_mapping(
            self.address_bar,
            "ui.address_placeholder",
            "setPlaceholderText",
            CANVAS_LOCALE_DOMAIN,
        )
        self.address_bar.setFixedHeight(nav_height - 8)
        self.address_bar.returnPressed.connect(self._on_address_enter)
        self.address_history_model = QStandardItemModel(self.address_bar)
        self.address_completer = AddressHistoryCompleter(self.address_history_model, self.address_bar)
        self.address_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.address_completer.setCompletionRole(Qt.DisplayRole)
        self.address_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.address_completer.setFilterMode(Qt.MatchContains)
        self.address_completer.setModelSorting(QCompleter.UnsortedModel)
        self.address_completer.setMaxVisibleItems(12)
        self.address_bar.setCompleter(self.address_completer)
        self.address_bar.textEdited.connect(self._on_address_text_edited)
        self.address_completer.activated[str].connect(self._on_history_selected)
        self._setup_address_history_popup_palette()

        self.btn_back.clicked.connect(lambda: self.tool.runtime_call("canvas_prev", {"__ui": True}))
        self.btn_next.clicked.connect(lambda: self.tool.runtime_call("canvas_next", {"__ui": True}))
        self.btn_reload.clicked.connect(lambda: self.tool.runtime_call("canvas_reload", {"__ui": True}))
        self.btn_home.clicked.connect(self.tool.open_start_page)
        self.btn_go.clicked.connect(self._on_address_enter)

        self.nav_layout.addWidget(self.btn_back)
        self.nav_layout.addWidget(self.btn_next)
        self.nav_layout.addWidget(self.btn_reload)
        self.nav_layout.addWidget(self.btn_home)
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
        self._hide_address_history_popup()
        text = self.address_bar.text().strip()
        if text:
            value = self._address_history_lookup.get(text, text)
            if value != text:
                self.address_bar.setText(value)
            self.tool.open_address(value)

    @staticmethod
    def _history_label(entry: dict) -> str:
        """Return a compact popup label without the HTTP(S) scheme."""
        url = str(entry.get("url") or "").strip()
        display_url = url
        lowered = display_url.lower()
        if lowered.startswith("https://"):
            display_url = display_url[8:]
        elif lowered.startswith("http://"):
            display_url = display_url[7:]
        title = " ".join(str(entry.get("title") or "").split())
        display_url = display_url.rstrip("/")
        if len(title) > 30:
            title = title[:30].rstrip() + "…"
        return f"{title} - {display_url}" if title else display_url

    def _setup_address_history_popup_palette(self):
        """Force the completer popup to use readable application palette colors."""
        if self.address_completer is None or self.address_bar is None:
            return
        popup = self.address_completer.popup()
        if popup is None:
            return
        palette = self.address_bar.palette()
        bg = palette.color(QPalette.Base).name()
        fg = palette.color(QPalette.Text).name()
        highlight = palette.color(QPalette.Highlight)
        sel_bg = highlight.name()
        sel_fg = palette.color(QPalette.HighlightedText).name()
        hover_bg = f"rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, 45)"
        popup.setMouseTracking(True)
        if popup.viewport() is not None:
            popup.viewport().setMouseTracking(True)
        popup.setStyleSheet(
            "QAbstractItemView {"
            f" background-color: {bg}; color: {fg};"
            " border: 0; outline: 0;"
            " border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;"
            "}"
            "QAbstractItemView::item { padding: 4px 6px; }"
            "QAbstractItemView::item:hover {"
            f" background-color: {hover_bg}; color: {fg};"
            "}"
            "QAbstractItemView::item:selected {"
            f" background-color: {sel_bg}; color: {sel_fg};"
            "}"
        )

    def _hide_address_history_popup(self):
        """Hide the history completer without changing the address text."""
        if self.address_completer is None:
            return
        popup = self.address_completer.popup()
        if popup is not None:
            popup.hide()

    def _on_history_selected(self, value: str):
        """Open the URL represented by a selected persistent-history row."""
        value = str(value or "").strip()
        # Compatibility fallback if a Qt style/platform emits the display label.
        value = self._address_history_lookup.get(value, value)
        if not value:
            return
        self._hide_address_history_popup()
        if self.address_bar is not None:
            self.address_bar.setText(value)
        self.tool.open_address(value)
        # QCompleter may try to restore its popup after activation on some Qt
        # styles/platforms. Hide it once more after that event is processed.
        QTimer.singleShot(0, self._hide_address_history_popup)

    def _on_address_text_edited(self, text: str):
        """Show history suggestions only after the user enters non-empty text."""
        if self.address_completer is None:
            return
        value = str(text or "")
        popup = self.address_completer.popup()
        if not value.strip() or not self._address_history_labels:
            if popup is not None:
                popup.hide()
            return
        self.address_completer.setCompletionPrefix(value)
        if popup is not None and self.address_bar is not None:
            popup.setMinimumWidth(self.address_bar.width())
        self._setup_address_history_popup_palette()
        self.address_completer.complete()

    def update_address_history(self, entries):
        """Refresh title + URL completion rows while preserving newest-first order."""
        normalized = []
        labels = []
        lookup = {}
        for item in entries or []:
            if isinstance(item, str):
                item = {"url": item, "title": ""}
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            entry = {"url": url, "title": str(item.get("title") or "").strip()}
            label = self._history_label(entry)
            # Very rare duplicate labels are made unique without changing the URL.
            base = label
            suffix = 2
            while label in lookup and lookup[label] != url:
                label = f"{base} ({suffix})"
                suffix += 1
            normalized.append(entry)
            labels.append(label)
            lookup[label] = url
        if normalized == self._address_history_entries and labels == self._address_history_labels:
            return
        self._address_history_entries = normalized
        self._address_history_labels = labels
        self._address_history_lookup = lookup
        if self.address_history_model is not None:
            self.address_history_model.clear()
            for entry, label in zip(normalized, labels):
                item = QStandardItem(label)
                item.setEditable(False)
                item.setData(entry["url"], Qt.UserRole)
                self.address_history_model.appendRow(item)

    def _sync_from_runtime(self):
        state = self.tool.current_state()
        self._hide_address_history_popup()
        if self.address_bar is not None:
            self.address_bar.setText(state.get("url", ""))
        self.update_address_history(self.tool.get_browser_history_entries())
        if self.btn_back is not None:
            self.btn_back.setEnabled(bool(state.get("can_go_back")))
        if self.btn_next is not None:
            self.btn_next.setEnabled(bool(state.get("can_go_forward")))
        if self.btn_reload is not None:
            self.btn_reload.setEnabled(True)

    def on_runtime_state(self, state: dict):
        self._sync_from_runtime()
        self._update_viewport_badge(state)
        # The application has one canonical Canvas tab, but its title
        # may still follow the currently rendered document.  This is only a
        # label update; it must never be used as tab identity.
        title = state.get("title") or ""
        if self.tab is not None and title and title != "about:blank":
            try:
                self.window.controller.tabs.update_title_by_tab(self.tab, title)
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

    def _display_footer_enabled(self) -> bool:
        """Return whether Canvas footer overlays are enabled for the active profile."""
        if self.tool is None:
            return True
        try:
            return bool(self.tool._opt("display_footer", True))
        except Exception:
            return True

    def _update_viewport_badge(self, state: dict):
        if self.viewport_badge is None:
            return
        width = int(state.get("width") or 0)
        height = int(state.get("height") or 0)
        self.viewport_badge.setText(f"{width} × {height}")
        self.viewport_badge.adjustSize()
        self.viewport_badge.setVisible(self._display_footer_enabled())
        self._position_viewport_overlays()

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
        # Chromium replaces its focus child; the shortcut follows the whole view.
        self._reload_shortcut = QShortcut(QKeySequence("F5"), self)
        self._reload_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self._reload_shortcut.activated.connect(
            lambda: self.tool.runtime_call("canvas_reload", {"__ui": True})
            if self.tool is not None else None
        )
        if tool is not None:
            self.signals.save_as.connect(tool.handle_save_as)
        if window is not None:
            self.signals.audio_read.connect(window.controller.chat.render.handle_audio_read)

    def reset_runtime_page(self):
        """Replace the WebEngine page so native history/DOM state cannot cross profiles."""
        self._detach_gl_event_filter()
        old_page = self.page()
        new_page = BrowserPage(tool=self.tool, parent=self)
        self.setPage(new_page)
        if old_page is not None and old_page is not new_page:
            old_page.deleteLater()

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

    def eventFilter(self, source, event):
        # QWebEngine gives keyboard focus to an internal render child, so F5
        # must also be intercepted by the event filter inherited from HtmlOutput.
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_F5 and self.tool is not None:
            self.tool.runtime_call("canvas_reload", {"__ui": True})
            event.accept()
            return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5 and self.tool is not None:
            self.tool.runtime_call("canvas_reload", {"__ui": True})
            event.accept()
            return
        super().keyPressEvent(event)

    def on_context_menu(self, position):
        menu = QMenu(self)
        selected = self.page().selectedText() if self.page().hasSelection() else ""
        if selected:
            copy_action = QAction(QIcon(":/icons/copy.svg"), trans("ui.copy", domain="plugin.canvas_web"), self)
            copy_action.triggered.connect(self.copy_selected_text)
            menu.addAction(copy_action)
            copy_to_menu = self.window.ui.context_menu.get_copy_to_menu(menu, selected)
            menu.addMenu(copy_to_menu)
            annotate = QAction(trans("ui.annotate_selection", domain="plugin.canvas_web"), self)
            annotate.triggered.connect(lambda: self.tool.annotate_selection(selected, position, backend="qt"))
            menu.addAction(annotate)
        else:
            annotate = QAction(QIcon(":/icons/chat3.svg"), trans("ui.annotate_element", domain="plugin.canvas_web"), self)
            annotate.triggered.connect(lambda: self.tool.annotate_at(position.x(), position.y(), backend="qt"))
            menu.addAction(annotate)
            select_all = QAction(trans("ui.select_all", domain="plugin.canvas_web"), self)
            select_all.triggered.connect(self.select_all_text)
            menu.addAction(select_all)
        menu.addSeparator()
        add_html_file_actions(menu, self.tool, self)
        menu.addSeparator()
        show_source = QAction(QIcon(":/icons/code.svg"), trans("ui.show_source", domain="plugin.canvas_web"), self)
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

    def clear_frame(self):
        self._pixmap = QPixmap()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._pixmap.isNull():
            painter.drawPixmap(self.rect(), self._pixmap)
        else:
            painter.fillRect(self.rect(), self.palette().base())
        if self.tool is not None and self.tool.cursor_visible:
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
        if event.key() == Qt.Key_F5 and self.tool is not None:
            self.tool.runtime_call("canvas_reload", {"__ui": True})
            event.accept()
            return
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
        annotate = QAction(QIcon(":/icons/chat3.svg"), trans("ui.annotate_element", domain="plugin.canvas_web"), self)
        annotate.triggered.connect(lambda: self.tool.annotate_at(p.x(), p.y(), backend="playwright"))
        menu.addAction(annotate)
        copy_to_menu = self.tool.window.ui.context_menu.get_copy_to_menu(
            menu,
            selected_text_provider=self.tool.get_selected_text,
        )
        menu.addMenu(copy_to_menu)
        menu.addSeparator()
        add_html_file_actions(menu, self.tool, self)
        menu.addSeparator()
        show_source = QAction(QIcon(":/icons/code.svg"), trans("ui.show_source", domain="plugin.canvas_web"), self)
        show_source.triggered.connect(self.tool.show_source)
        menu.addAction(show_source)
        menu.exec_(event.globalPos())


class SourceEditor(TextEditor):
    """HTML source editor for the current browser document."""

    def __init__(self, tool=None, parent=None):
        self.tool = tool
        window = tool.window if tool is not None else getattr(parent, "window", None)
        super().__init__(
            window=window,
            parent=parent,
            path="canvas.html",
            line_numbers=True,
            syntax_highlighting=True,
            tabs=True,
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5 and self.tool is not None:
            self.tool.runtime_call("canvas_reload", {"__ui": True})
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        selected = self.textCursor().selection().toPlainText()
        if selected:
            menu.addMenu(self.tool.window.ui.context_menu.get_copy_to_menu(menu, selected))
        if menu.actions():
            menu.addSeparator()
        add_html_file_actions(menu, self.tool, self)
        menu.addSeparator()
        back = QAction(QIcon(":/icons/fullscreen.svg"), trans("ui.back_to_canvas", domain="plugin.canvas_web"), self)
        back.triggered.connect(self.tool.show_canvas)
        menu.addAction(back)
        menu.addSeparator()
        self.add_word_wrap_action(menu)
        menu.exec_(event.globalPos())


class BrowserViewport(QWidget):
    """Persistent browser viewport with rendered and editable-source modes."""

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

    def reset_session(self):
        """Clear all visible page/editor/frame state before a profile switch."""
        self._source_loading = True
        try:
            self.source.clear()
            self.source.document().setModified(False)
            self._source_base_url = ""
            self._source_visible = False
        finally:
            self._source_loading = False
        self.web.reset_runtime_page()
        self.sandbox.clear_frame()
        self.set_mode("qt")

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
        # Source editing is intentionally detached from the live renderer.
        # Apply the document once, only when returning to the HTML view.
        if self._source_visible and self.source.document().isModified():
            self._apply_source()
        self._source_visible = False
        self.set_mode(self._mode)
        self.active_view().setFocus(Qt.OtherFocusReason)

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
        try:
            self.source.on_destroy()
        except Exception:
            pass
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
    def __init__(self, on_return_callback=None, on_reload_callback=None, on_click_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_return_callback = on_return_callback
        self._on_reload_callback = on_reload_callback
        self._on_click_callback = on_click_callback
        self._select_all_on_click = True
        self._context_selection = None

    def focusOutEvent(self, event):
        # The next mouse visit starts a new address-editing interaction.
        self._select_all_on_click = True
        super().focusOutEvent(event)

    def _remember_context_selection(self):
        self._context_selection = (
            self.selectionStart(),
            self.selectionLength(),
            self.cursorPosition(),
        )

    def _restore_context_selection(self):
        if self._context_selection is None:
            return
        selection_start, selection_length, cursor_position = self._context_selection
        if selection_start >= 0 and selection_length > 0:
            self.setSelection(selection_start, selection_length)
        else:
            self.deselect()
            self.setCursorPosition(cursor_position)

    def mousePressEvent(self, event):
        """Select all on first LMB click; RMB must not alter cursor/selection."""
        if event.button() == Qt.RightButton:
            # Do not pass RMB to QLineEdit at all. Depending on platform/style,
            # the native press/release handling may move the cursor or clear the
            # selection before QContextMenuEvent arrives, which disables Copy.
            self._remember_context_selection()
            event.accept()
            return

        select_all = self._select_all_on_click and event.button() == Qt.LeftButton
        if event.button() == Qt.LeftButton:
            self._select_all_on_click = False
        super().mousePressEvent(event)
        if select_all:
            # QLineEdit applies the click cursor position during the mouse event,
            # so defer selection until that processing has completed. Subsequent
            # clicks while the field stays focused behave normally.
            QTimer.singleShot(0, self.selectAll)
        if event.button() == Qt.LeftButton and callable(self._on_click_callback):
            QTimer.singleShot(0, self._on_click_callback)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            # Keep the whole RMB gesture inert with regard to the editor state.
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        # Restore once more immediately before creating the standard menu: its
        # Copy action is enabled from the selection state at creation time.
        self._restore_context_selection()
        menu = self.createStandardContextMenu()
        menu.exec(event.globalPos())
        menu.deleteLater()
        self._context_selection = None
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            if callable(self._on_reload_callback):
                self._on_reload_callback()
            event.accept()
            return
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
