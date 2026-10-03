#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import threading
import time
import uuid
from typing import Dict, Optional

from PySide6.QtCore import QTimer, QUrl, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget

from pygpt_net.ui.widget.textarea.annotations import AnnotationMixin
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.types.canvas import CanvasSearchEngine
from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool, TabWidget, ToolMenuAction
from pygpt_net.utils import trans

from .ui.widgets import ToolSignals, BrowserViewport
from .ui.dialogs import Tool

from .core.scripts import BLANK_CANVAS_HTML_LIGHT, BLANK_CANVAS_HTML_DARK, BLANK_CANVAS_HTML, JS_SERIALIZE_HTML, JS_INSPECT
from .core.commands import CanvasCommands
from .core.playwright import PlaywrightBackend
from .core.preview import PreviewServer
from .core.history import CanvasHistory
from .core.document import CanvasDocument
from .core.viewport import CanvasViewport
from .core.qt import QtBackend
from .core.annotations import CanvasAnnotations


class WebBrowser(AnnotationMixin, BaseTool):
    """Canvas entry point and coordinator for independent browser sessions.

    The registered tool manages surfaces; each surface receives an independent
    runtime with its own composed services. Shared session state stays here so
    widgets and plugins share the selected session. Implement behavior in the
    responsible service. Call components directly rather than adding wrappers.
    """

    HISTORY_LIMIT = 30
    BROWSER_HISTORY_FILE = "browser_history.json"

    BLANK_CANVAS_HTML_LIGHT = BLANK_CANVAS_HTML_LIGHT

    BLANK_CANVAS_HTML_DARK = BLANK_CANVAS_HTML_DARK

    # Compatibility alias for callers/tests that reference the old constant.
    BLANK_CANVAS_HTML = BLANK_CANVAS_HTML

    JS_SERIALIZE_HTML = JS_SERIALIZE_HTML

    JS_INSPECT = JS_INSPECT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands = CanvasCommands(self)
        self.playwright = PlaywrightBackend(self)
        self.preview = PreviewServer(self)
        self.history = CanvasHistory(self)
        self.document = CanvasDocument(self)
        self.viewport = CanvasViewport(self)
        self.qt = QtBackend(self)
        self.annotation_bridge = CanvasAnnotations(self)
        self.id = "web_browser"
        self.allow_tab = True
        self.allow_dialog = True
        self.multi_tab = True
        self.multi_dialog = True
        self.on_menu_click = ToolMenuAction.DIALOG_IF_TAB_EXISTS
        self.dialog_id = "web_browser"
        self.tab_title = "tool.web_browser.tab_title"
        self.dialog_opener = "open_window"
        self.runtime_root = None
        self.tab_icon = ":/icons/grid.svg"
        self.opened = False
        self.dialog = None
        self.signals = ToolSignals()
        self.surface: Optional[BrowserViewport] = None
        self.surface_owner = None
        self.hidden_host = None
        self.hidden_layout = None

        self.backend = "qt"  # qt | playwright
        self.agent_backend_locked = False
        self.width = 1280
        self.height = 800
        self.orientation = "landscape"
        # The visible Canvas tab follows the actual Qt viewport size. Keep the
        # model-requested resolution separately so UI fitting never destroys the
        # resolution the agent expects when the split-screen column is hidden.
        self.model_resolution = None
        self.ui_viewport_target = None
        self.ui_viewport_visible = False
        self.viewport_policy_timer = QTimer(self)
        self.viewport_policy_timer.setSingleShot(True)
        self.viewport_policy_timer.timeout.connect(self.viewport.apply_viewport_policy)
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = False
        self.virtual_url = "about:blank"
        self.base_url = ""
        self.console = []
        self.annotations = []
        self.annotation_seq = 0

        self.pw = None
        self._playwright_driver = None
        self._playwright_users = set()
        self.pw_browser = None
        self.pw_context = None
        self.pw_page = None
        self.pw_frame_pending = False
        self.pw_history = []
        self.pw_history_index = -1
        self.pw_history_mode = None
        self.pw_frame_timer = None

        self.server = None
        self.server_thread = None
        self.server_root = None
        self.server_url = None
        self.runtime_html = ""
        self.blank_canvas_active = False

        # Canvas-level navigation history. QWebEngine does not create a useful
        # history item for setHtml(), so keep URL and HTML entries together here.
        # This also gives the Playwright backend the same Back/Forward semantics.
        self.canvas_history = []
        self.canvas_history_index = -1
        self._history_loading = False
        self._source_reload_pending = False

        # Persistent address history is intentionally separate from the Canvas
        # Back/Forward history above. It stores only visited HTTP(S) URLs and is
        # profile/workdir-scoped in browser_history.json.
        self.browser_history = []
        self._browser_history_lock = threading.RLock()

    def setup(self):
        self.history.load()
        self.update()

    def post_setup(self):
        # Keep WebEngine/Playwright lazy. The persistent runtime is created on
        # first manual or agent use, so enabling the base tool has no startup cost.
        pass

    def on_reload(self):
        self.history.load()
        for entry in list(self._surfaces):
            entry['instance'].on_reload()
        self.update()
        # Canvas is profile-scoped. If a runtime already exists, discard the
        # previous profile's page/session state and start the new profile from
        # its configured start page. Keep WebEngine lazy when Canvas was never
        # created in this application session.
        if self.surface is not None:
            self.reset_profile_runtime()
        else:
            self.setup_theme()

    def on_exit(self):
        for entry in list(self._surfaces):
            self.release_runtime(entry['instance'])
        self.viewport_policy_timer.stop()
        if self.pw_frame_timer is not None:
            self.pw_frame_timer.stop()
        self.preview.stop()
        self.playwright.stop()
        if self.surface is not None:
            self.surface.shutdown()
            self.surface.deleteLater()
            self.surface = None
        if self.hidden_host is not None:
            self.hidden_host.deleteLater()
            self.hidden_host = None

    def update(self):
        self.update_menu()

    def update_menu(self):
        pass

    def _plugin(self):
        return self.window.core.plugins.get("canvas_web") if self.window else None

    def _opt(self, key, default=None):
        plugin = self._plugin()
        if plugin is None:
            return default
        try:
            value = plugin.get_option_value(key)
            return default if value is None else value
        except Exception:
            return default

    def current_canvas_history_is_url(self) -> bool:
        if not (0 <= self.canvas_history_index < len(self.canvas_history)):
            return False
        return self.canvas_history[self.canvas_history_index].get("kind") == "url"

    def sandbox_enabled(self) -> bool:
        """Return whether Playwright is explicitly enabled in plugin settings."""
        return bool(self._opt("use_sandbox", False))

    def auto_open_enabled(self) -> bool:
        """Return whether Canvas should be surfaced automatically when used."""
        try:
            return bool(self.window.core.config.get("layout.canvas.auto_open", True))
        except Exception:
            return True

    def start_page(self) -> str:
        """Return the profile start page, normalizing an empty value to about:blank."""
        value = str(self._opt("start_page", "about:blank") or "").strip()
        return value or "about:blank"

    def search_engine(self) -> CanvasSearchEngine:
        return CanvasSearchEngine.from_value(self._opt("default_search_engine", CanvasSearchEngine.GOOGLE.value))

    def load_start_page(self):
        """Load the configured profile start page without opening/focusing a Canvas tab."""
        return self.commands.open({
            "url": self.start_page(),
            "__ui": True,
            "__startup": True,
        })

    def reset_profile_runtime(self):
        """Drop all browser/session state that must not survive a profile switch."""
        self.preview.stop()
        self.playwright.stop()
        self.backend = "qt"
        self.agent_backend_locked = False
        self.model_resolution = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_visible = False
        self.virtual_url = "about:blank"
        self.base_url = ""
        self.console = []
        self.annotations = []
        self.annotation_seq = 0
        self._notify_annotation_count_changed()
        self.runtime_html = ""
        self.blank_canvas_active = False
        self.canvas_history = []
        self.canvas_history_index = -1
        self._history_loading = False
        self._source_reload_pending = False

        width = int(self._opt("default_width", 1280) or 1280)
        height = int(self._opt("default_height", 800) or 800)
        if self.surface is not None:
            self.surface.reset_session()
            self.surface.set_mode("qt")
            self.viewport.set_resolution(width, height, "auto")
        else:
            self.width = width
            self.height = height
            self.orientation = "landscape" if width >= height else "portrait"

        self.load_start_page()
        self.notify_state()

    def blank_canvas_html(self) -> str:
        """Return the empty Canvas grid matching the active light/dark theme."""
        is_dark = True
        try:
            is_dark = self.window.controller.theme.is_dark_theme()
        except Exception:
            try:
                is_dark = str(self.window.core.config.get("theme", "dark")).lower() != "light"
            except Exception:
                pass
        return self.BLANK_CANVAS_HTML_DARK if is_dark else self.BLANK_CANVAS_HTML_LIGHT

    def render_blank_canvas(self):
        """Render the theme-aware synthetic page used by an empty Canvas."""
        html = self.blank_canvas_html()
        self.blank_canvas_active = True
        self.virtual_url = "about:blank"
        if self.backend == "playwright":
            self.playwright.ensure()
            self.pw_page.set_content(html, wait_until="domcontentloaded")
            self.playwright.refresh_frame()
        elif self.surface is not None:
            self.surface.web.setHtml(html, QUrl("about:blank"))

    def get_dialog_id(self) -> str:
        return self.dialog_id

    def set_url(self, url: str):
        """Show/focus Canvas and then open *url* in the internal browser."""
        self.open(load=False)
        return self.runtime_call("canvas_open", {"url": url, "__ui": True})

    def open_address(self, value: str):
        """Open an address-bar value, converting plain text to a web search."""
        target = self.document.address_target(value)
        if not target:
            return self.current_state()
        return self.runtime_call("canvas_open", {"url": target, "__ui": True})

    def open_start_page(self):
        """Open the start page configured for the active profile."""
        return self.runtime_call("canvas_open", {
            "url": self.start_page(),
            "__ui": True,
        })

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = "txt"):
        """Keep the legacy Web Browser save hook available for UI compatibility."""
        if type == "html":
            text = output_clean_html(text)
        else:
            text = output_html2text(text)
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text, type))

    def setup_menu(self) -> Dict[str, QAction]:
        actions = {}
        actions["web_browser"] = QAction(
            QIcon(":/icons/grid.svg"),
            trans("menu.tools.canvas_html"),
            self.window,
            checkable=False,
        )
        actions["web_browser"].triggered.connect(self.on_menu_action)
        return actions

    def get_lang_mappings(self) -> Dict[str, Dict]:
        return {
            "menu.text": {
                "tools.web_browser": "menu.tools.canvas_html",
            }
        }

    def get_annotations(self):
        if self.runtime_root is not None or self.window is None:
            return super().get_annotations()
        runtime = self.resolve_surface()
        return runtime.get_annotations() if runtime is not None else []

    # ------------------------------------------------------------------
    # Main-thread runtime API
    # ------------------------------------------------------------------

    def runtime_call(self, cmd: str, params: dict, plugin=None):
        if self.runtime_root is None:
            runtime = self.resolve_surface(create=True, activate=True)
            return runtime.runtime_call(cmd, params, plugin=plugin)
        self.runtime_root.mark_surface_used(self)
        return self.commands.execute(cmd, params, plugin=plugin)

    # ------------------------------------------------------------------
    # Playwright backend
    # ------------------------------------------------------------------

    def set_backend(self, mode: str):
        mode = "playwright" if mode == "playwright" else "qt"
        if self.backend == mode:
            self.surface.set_mode(mode)
            if mode == "playwright":
                self.playwright.ensure()
            return
        previous = self.backend
        if mode == "playwright":
            try:
                self.playwright.ensure()
            except Exception:
                self.backend = previous
                self.surface.set_mode(previous)
                raise
        elif self.pw_page is not None:
            self.playwright.stop()
        self.backend = mode
        self.surface.set_mode(mode)
        self.notify_state()

    def current_url(self):
        if self.backend == "playwright" and self.pw_page is not None:
            try:
                url = self.pw_page.url
                if (not url or url == "about:blank") and self.virtual_url:
                    return self.virtual_url
                return url or self.virtual_url
            except Exception:
                return self.virtual_url
        try:
            url = self.surface.web.url().toString()
            return url or self.virtual_url
        except Exception:
            return self.virtual_url

    def current_state(self):
        title = ""
        can_back = False
        can_forward = False
        if self.backend == "playwright" and self.pw_page is not None:
            try:
                title = self.pw_page.title()
                can_back = self.pw_history_index > 0
                can_forward = self.pw_history_index + 1 < len(self.pw_history)
            except Exception:
                pass
        else:
            try:
                title = self.surface.web.title()
                hist = self.surface.web.history()
                can_back = bool(hist.canGoBack())
                can_forward = bool(hist.canGoForward())
            except Exception:
                pass
        owner = self.surface_owner
        ui_surface = "background"
        if owner is not None:
            ui_surface = getattr(owner, "surface_kind", "tab")
        return {
            "url": self.current_url(), "title": title, "backend": self.backend,
            "sandbox": self.backend == "playwright", "sandbox_enabled": self.sandbox_enabled(),
            "width": self.width, "height": self.height,
            "resolution": f"{self.width}x{self.height}", "orientation": self.orientation,
            "cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "base_url": self.base_url,
            "can_go_back": (self.canvas_history_index > 0) if self.canvas_history else can_back,
            "can_go_forward": (self.canvas_history_index + 1 < len(self.canvas_history)) if self.canvas_history else can_forward,
            "history_length": len(self.canvas_history),
            "ui_surface": ui_surface, "session_alive": True,
            "server": self.preview.state(), "annotations": len(self.annotations),
        }

    def notify_state(self):
        state = self.current_state()
        try:
            self.signals.state.emit(state)
        except Exception:
            pass
        if self.surface_owner is not None:
            try:
                self.surface_owner.on_runtime_state(state)
            except Exception:
                pass
        if self.surface is not None and self.backend == "playwright":
            self.surface.sandbox.update()

    def append_qt_console(self, level, message, line_number=0, source_id=""):
        """Forward QWebEngine console output into the shared browser console buffer."""
        level_name = str(level).rsplit(".", 1)[-1]
        source = str(source_id or "qt-webengine")
        text = str(message)
        if line_number:
            text = f"{text} (line {int(line_number)})"
        self.append_console(source, level_name, text)

    def append_console(self, source, level, message):
        if self.runtime_root is None and self._surfaces:
            runtime = self.resolve_surface()
            if runtime is not None:
                return runtime.append_console(source, level, message)
        level_text = str(level)
        message_text = str(message)
        self.console.append({"time": time.time(), "source": source, "level": level_text, "message": message_text})
        limit = max(10, int(self._opt("console_limit", 200) or 200))
        if len(self.console) > limit:
            del self.console[:-limit]

        # JavaScript/page/runtime errors are non-modal. Keep them visible in the
        # app log and bottom status bar without interrupting browser automation.
        if "error" in level_text.lower():
            try:
                self.window.core.debug.log(f"{trans('menu.tools.canvas_html')} [{source}]: {message_text}")
            except Exception:
                pass
            try:
                self.window.update_status(f"{trans('menu.tools.canvas_html')}: {message_text}")
            except Exception:
                pass

    def new_runtime(self):
        runtime = type(self)()
        runtime.runtime_root = self
        runtime.attach(self.window)
        runtime.setParent(self)
        return runtime

    def create_surface(self):
        if not self.can_open_tab():
            if self.can_open_dialog():
                return self.open_window()
            raise RuntimeError("Canvas tabs and dialogs are disabled")
        tabs = self.window.controller.tabs
        if not self.can_add_tab():
            tab = self.existing_tab()
            entry = next((entry for entry in self._surfaces if entry['tab'] is tab), None)
            if entry is None:
                raise RuntimeError("Existing Canvas tab has no registered runtime")
            return entry['instance']
        previous = {id(entry['instance']) for entry in self._surfaces}
        idx = max(0, self.window.core.tabs.get_max_idx_by_column(1))
        tabs.append(type=Tab.TAB_TOOL, tool_id=self.id, idx=idx, column_idx=1)
        entry = next((entry for entry in self._surfaces
                      if id(entry['instance']) not in previous), None)
        if entry is None:
            raise RuntimeError("Canvas tab creation did not register a runtime")
        return entry['instance']

    def open(self, load: bool = True):
        if self.runtime_root is not None:
            return self.runtime_root.activate_runtime(self)
        return self.resolve_surface(create=True, activate=True)

    def open_tab(self):
        if not self.can_open_tab():
            return None
        runtime = self.create_surface()
        return self.activate_runtime(runtime)

    def activate_runtime(self, runtime):
        self.mark_surface_used(runtime)
        return self.resolve_surface(activate=True)

    def auto_open(self, load: bool = True):
        if self.auto_open_enabled():
            self.ensure_visible_surface()

    def ensure_agent_surface(self):
        runtime = self.runtime_root or self
        selected = runtime.resolve_surface(create=True, activate=True)
        return 'tab' if selected.surface_owner.tab is not None else 'dialog'

    def ensure_visible_surface(self):
        if self.runtime_root is not None:
            return self.runtime_root.activate_runtime(self)
        return self.resolve_surface(create=True, activate=True)

    def open_window(self):
        if not self.can_open_dialog():
            return None
        if not self.multi_dialog:
            for entry in self._surfaces:
                if entry['tab'] is None:
                    self.mark_surface_used(entry['instance'])
                    entry['widget'].show()
                    return self.resolve_surface(activate=True)
        from .ui.dialogs import CanvasDialog
        runtime = self.new_runtime()
        dialog_id = (self.dialog_id + '.' + uuid.uuid4().hex
                     if self.multi_dialog else self.dialog_id)
        try:
            dialog = CanvasDialog(self.window, dialog_id, runtime, self)
        except Exception:
            self.release_runtime(runtime)
            raise
        self.window.ui.dialog[dialog_id] = dialog
        self.register_surface(runtime, dialog, dialog_id=dialog_id)
        dialog.show()
        self.mark_surface_used(runtime)
        dialog.raise_()
        dialog.activateWindow()
        return runtime

    def close(self):
        """Hide/close the Canvas tab UI while preserving browser runtime."""
        return self.close_surface()

    def toggle(self):
        # Programmatic toggling opens/focuses the selected runtime.
        return self.open()

    def show_hide(self, show: bool = True):
        if show:
            self.open()
        else:
            self.close()

    def get_toolbar_icon(self) -> QWidget:
        return self.window.ui.nodes["icon.web_browser"]

    def toggle_icon(self, state: bool):
        self.get_toolbar_icon().setVisible(state)

    def close_surface(self):
        root = self.runtime_root or self
        runtime = self if self.runtime_root is not None else root.resolve_surface()
        entry = next((entry for entry in root._surfaces
                      if entry['instance'] is runtime), None)
        if entry is None:
            return {"closed": "none", "session_alive": False}
        if entry['tab'] is not None:
            tab = entry['tab']
            self.window.controller.tabs.close(tab.idx, tab.column_idx)
            kind = 'tab'
        else:
            entry['widget'].close()
            kind = 'dialog'
        return {"closed": kind, "session_alive": False}

    def as_tab(self, tab: Tab) -> QWidget:
        if not self.can_open_tab():
            return None
        runtime = self.new_runtime()
        tool = Tool(window=self.window, tool=runtime, surface_kind="tab")
        tool_widget = tool.as_tab()
        widget = TabWidget()
        widget.from_tool(tool_widget)
        tool.set_tab(tab)
        self.register_surface(runtime, widget, tab=tab)
        try:
            widget.setup()
        except Exception:
            self.release_runtime(runtime)
            raise
        return widget

    def release_runtime(self, runtime):
        self.unregister_surface(runtime)
        if runtime.surface_owner is not None:
            runtime.surface_owner._disconnect_viewport_hooks()
        runtime.on_exit()
        runtime.deleteLater()
        self._notify_annotation_count_changed()

    def setup_dialogs(self):
        # Frontends and browser engines are created lazily.
        self.dialog = None

    def apply_lang_mappings(self):
        super().apply_lang_mappings()
        for entry in self._surfaces:
            entry['instance'].apply_lang_mappings()

    def setup_theme(self):
        for entry in self._surfaces:
            entry['instance'].setup_theme()
        # Never touch user/model content on a theme change. Only the synthetic
        # empty Canvas page is regenerated so a live theme/profile switch cannot
        # leave a bright light grid inside the dark application theme.
        if self.surface is not None and self.blank_canvas_active:
            self.render_blank_canvas()

    def _show_annotation_editor(self, x: int, y: int, prefer_selection: bool, selected_hint: str, backend=None):
        backend = backend or self.backend
        script = self._annotation_editor_script(x, y, prefer_selection, selected_hint, backend)
        try:
            if backend == "playwright":
                self.playwright.ensure()
                self.pw_page.evaluate(script)
                self.playwright.schedule_frame(10)
            else:
                # Never block the GUI thread waiting for WebEngine JS. The editor
                # appears from the page callback itself and reports the completed
                # annotation through the private console bridge.
                self.surface.web.page().runJavaScript(script)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass

    def _render_annotations(self):
        if self.surface is None or self._history_loading:
            return
        script = self._annotation_overlay_script()
        try:
            if self.backend == "playwright":
                if self.pw_page is None:
                    return
                self.pw_page.evaluate(script)
                self.playwright.schedule_frame(10)
            else:
                # Async avoids nesting an event loop when called from a WebEngine
                # navigation callback or context-menu action.
                self.surface.web.page().runJavaScript(script)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass
