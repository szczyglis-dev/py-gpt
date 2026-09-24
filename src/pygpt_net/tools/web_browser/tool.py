#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 12:31:00
# ================================================== #

import json
import os
import threading
import time
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin

from PySide6.QtCore import QEventLoop, QTimer, QUrl, Slot, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool, TabWidget
from pygpt_net.utils import trans

from .ui.dialogs import Tool
from .ui.widgets import ToolSignals, BrowserViewport


class _PreviewHandler(SimpleHTTPRequestHandler):
    """Loopback preview handler which never follows symlinks outside its configured root."""

    RUNTIME_PATH = "/__pygpt_runtime__.html"

    def __init__(self, *args, runtime_html_getter=None, **kwargs):
        self.runtime_html_getter = runtime_html_getter
        super().__init__(*args, **kwargs)

    def _runtime_html(self):
        if self.path.split("?", 1)[0] != self.RUNTIME_PATH or not callable(self.runtime_html_getter):
            return None
        value = self.runtime_html_getter()
        return "" if value is None else str(value)

    def do_GET(self):
        runtime_html = self._runtime_html()
        if runtime_html is None:
            return super().do_GET()
        data = runtime_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self):
        runtime_html = self._runtime_html()
        if runtime_html is None:
            return super().do_HEAD()
        data = runtime_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def translate_path(self, path):
        translated = super().translate_path(path)
        root = os.path.realpath(self.directory or os.getcwd())
        target = os.path.realpath(translated)
        try:
            inside = os.path.commonpath([root, target]) == root
        except ValueError:
            inside = False
        if not inside:
            return os.path.join(root, ".__pygpt_forbidden__")
        return target

    def log_message(self, fmt, *args):
        return


class WebBrowser(BaseTool):
    """Single persistent browser runtime exposed through one Canvas tab."""

    BLANK_CANVAS_HTML_LIGHT = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {
    width: 100%;
    min-height: 100%;
    margin: 0;
}
body {
    min-height: 100vh;
    background-color: #f5f5f5;
    background-image:
        linear-gradient(rgba(0, 0, 0, 0.055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 0, 0, 0.055) 1px, transparent 1px);
    background-size: 24px 24px;
}
</style>
</head>
<body></body>
</html>"""

    BLANK_CANVAS_HTML_DARK = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {
    width: 100%;
    min-height: 100%;
    margin: 0;
}
body {
    min-height: 100vh;
    background-color: #1b1c1f;
    background-image:
        linear-gradient(#2a2c30 1px, transparent 1px),
        linear-gradient(90deg, #2a2c30 1px, transparent 1px);
    background-size: 24px 24px;
}
</style>
</head>
<body></body>
</html>"""

    # Compatibility alias for callers/tests that reference the old constant.
    BLANK_CANVAS_HTML = BLANK_CANVAS_HTML_LIGHT

    JS_SERIALIZE_HTML = r"""(() => {
      const root = document.documentElement.cloneNode(true);
      const cursor = root.querySelector('#__pygpt_virtual_cursor');
      if (cursor) cursor.remove();
      const annotations = root.querySelector('#__pygpt_annotations_root');
      if (annotations) annotations.remove();
      const annotationEditor = root.querySelector('#__pygpt_annotation_editor');
      if (annotationEditor) annotationEditor.remove();
      root.querySelectorAll('[data-pygpt-ref]').forEach(el => el.removeAttribute('data-pygpt-ref'));
      const dt = document.doctype ? '<!DOCTYPE ' + document.doctype.name + '>' : '';
      return dt + root.outerHTML;
    })()"""

    JS_INSPECT = r"""
(() => {
  const selector = %s;
  const limit = %d;
  const nodes = selector ? Array.from(document.querySelectorAll(selector)) : Array.from(document.querySelectorAll(
    'a,button,input,textarea,select,summary,[role="button"],[role="link"],[contenteditable="true"],[onclick]'
  ));
  const out = [];
  window.__pygpt_ref_seq = Number(window.__pygpt_ref_seq || 0);
  for (const el of nodes) {
    if (out.length >= limit) break;
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    if (r.width <= 0 || r.height <= 0 || st.visibility === 'hidden' || st.display === 'none') continue;
    let ref = el.getAttribute('data-pygpt-ref');
    if (!ref) {
      ref = 'e' + (++window.__pygpt_ref_seq);
      el.setAttribute('data-pygpt-ref', ref);
    }
    out.push({
      ref,
      selector: `[data-pygpt-ref="${ref}"]`,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 500),
      href: el.href || '',
      disabled: !!el.disabled,
      checked: !!el.checked,
      x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height)
    });
  }
  return out;
})()
"""

    def __init__(self, *args, **kwargs):
        super(WebBrowser, self).__init__(*args, **kwargs)
        self.id = "web_browser"
        self.dialog_id = "web_browser"
        self.has_tab = True
        self.single_instance = True
        self.tab_title = "menu.tools.canvas_html"
        self.tab_icon = ":/icons/grid.svg"
        self.opened = False
        self.dialog = None
        self.signals = ToolSignals()
        self.surface: Optional[BrowserViewport] = None
        self.surface_owner = None
        self.hidden_host = None
        self.hidden_layout = None
        self.split_auto_expanded = False

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
        self.viewport_policy_timer.timeout.connect(self._apply_viewport_policy)
        self.cursor_x = 0
        self.cursor_y = 0
        self.virtual_url = "about:blank"
        self.base_url = ""
        self.console = []
        self.annotations = []
        self.annotation_seq = 0

        self.pw = None
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

    def setup(self):
        self.update()

    def post_setup(self):
        # Keep WebEngine/Playwright lazy. The persistent runtime is created on
        # first manual or agent use, so enabling the base tool has no startup cost.
        pass

    def on_reload(self):
        self.update()
        # Profile reloads can change the light/dark theme while the persistent
        # Canvas runtime stays alive. Refresh only the synthetic empty page.
        self.setup_theme()

    def on_exit(self):
        self._stop_server()
        self._stop_playwright()
        if self.surface is not None:
            self.surface.shutdown()
            self.surface = None

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

    def _sandbox_enabled(self) -> bool:
        """Return whether Playwright is explicitly enabled in plugin settings."""
        return bool(self._opt("use_sandbox", False))

    def _blank_canvas_html(self) -> str:
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

    def _render_blank_canvas(self):
        """Render the theme-aware synthetic page used by an empty Canvas."""
        html = self._blank_canvas_html()
        self.blank_canvas_active = True
        self.virtual_url = "about:blank"
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.set_content(html, wait_until="domcontentloaded")
            self._refresh_playwright_frame()
        elif self.surface is not None:
            self.surface.web.setHtml(html, QUrl("about:blank"))

    def _ensure_surface(self):
        if self.surface is not None:
            return self.surface
        self.width = int(self._opt("default_width", 1280) or 1280)
        self.height = int(self._opt("default_height", 800) or 800)
        self.orientation = "landscape" if self.width >= self.height else "portrait"
        self.hidden_host = QWidget(self.window)
        self.hidden_layout = QVBoxLayout(self.hidden_host)
        self.hidden_layout.setContentsMargins(0, 0, 0, 0)
        self.surface = BrowserViewport(self.window, self)
        self.surface.set_resolution(self.width, self.height)
        # Give a newly created/empty canvas a subtle theme-aware grid instead
        # of QWebEngine's plain white about:blank page. Any real navigation or
        # canvas_set_html call replaces this document normally.
        self._render_blank_canvas()
        self.hidden_layout.addWidget(self.surface)
        self.pw_frame_timer = QTimer(self)
        self.pw_frame_timer.setInterval(250)
        self.pw_frame_timer.timeout.connect(self._poll_playwright_frame)
        self.hidden_host.hide()
        try:
            self.surface.web.urlChanged.connect(lambda _url: self._notify_state())
            self.surface.web.titleChanged.connect(lambda _title: self._notify_state())
        except Exception:
            pass
        return self.surface

    def attach_surface(self, owner):
        surface = self._ensure_surface()
        if self.surface_owner is owner:
            owner.attach_runtime_surface(surface)
            return
        if self.surface_owner is not None:
            try:
                self.surface_owner._take_surface()
            except Exception:
                pass
        else:
            try:
                self.hidden_layout.removeWidget(surface)
            except Exception:
                pass
        surface.setParent(None)
        self.surface_owner = owner
        owner.attach_runtime_surface(surface)
        if getattr(owner, "tab", None) is not None:
            surface.set_tab(owner.tab)
        self._notify_state()
        try:
            owner.request_viewport_sync(immediate=True)
        except Exception:
            pass

    def detach_surface(self, owner=None):
        if self.surface is None:
            return
        if owner is not None and self.surface_owner is not owner:
            return
        if self.surface_owner is not None:
            try:
                self.surface_owner._take_surface()
            except Exception:
                pass
        self.surface_owner = None
        if self.hidden_layout is not None:
            self.surface.setParent(self.hidden_host)
            self.hidden_layout.addWidget(self.surface)
        self.request_viewport_policy(visible=False, delay=0)
        self._notify_state()

    def _app_busy(self) -> bool:
        """Return True while the application/model request is actively running."""
        try:
            kernel = getattr(self.window.controller, "kernel", None)
            if kernel is not None:
                return bool(getattr(kernel, "busy", False))
        except Exception:
            pass
        try:
            return getattr(self.window, "state", None) == getattr(self.window, "STATE_BUSY", "busy")
        except Exception:
            return False

    def request_viewport_policy(self, width=None, height=None, visible=True, delay: int = 0):
        """Queue Canvas viewport synchronization with the current UI geometry.

        Visible Canvas uses the real available column area. A fully hidden
        Canvas uses the last model-requested resolution, or plugin defaults when
        the model has not selected a resolution yet. While the app is BUSY the
        request is retained and applied only after it returns to IDLE.
        """
        self.ui_viewport_visible = bool(visible)
        if visible and width is not None and height is not None:
            width = int(width)
            height = int(height)
            if width > 0 and height > 0:
                self.ui_viewport_target = (width, height)
        if self.viewport_policy_timer is None:
            return
        self.viewport_policy_timer.start(max(0, int(delay)))

    def _hidden_resolution(self):
        """Return the runtime size used while the Canvas column is fully hidden."""
        if self.model_resolution is not None:
            return self.model_resolution
        width = int(self._opt("default_width", 1280) or 1280)
        height = int(self._opt("default_height", 800) or 800)
        return max(240, min(width, 7680)), max(180, min(height, 4320))

    def _apply_viewport_policy(self):
        """Apply a queued UI/background viewport transition when it is safe."""
        if self.surface is None:
            return
        if self._app_busy():
            # Do not compete with canvas_change_resolution while the model is
            # using the runtime. Keep retrying until the application is IDLE.
            self.viewport_policy_timer.start(120)
            return

        if self.ui_viewport_visible and self.ui_viewport_target is not None:
            width, height = self.ui_viewport_target
            changed = self._set_resolution(width, height, "auto", clamp_min=False)
        else:
            width, height = self._hidden_resolution()
            changed = self._set_resolution(width, height, "auto", clamp_min=True)

        if changed:
            self._notify_state()

    def get_dialog_id(self) -> str:
        return self.dialog_id

    def set_url(self, url: str):
        self.runtime_call("canvas_open", {"url": url, "__ui": True})

    def open(self, load: bool = True):
        """Open/focus the single Canvas tab in the second column."""
        self._ensure_surface()
        tabs = self.window.controller.tabs
        tab = tabs.get_first_tab_by_tool(self.id)

        if tab is None:
            idx = self.window.core.tabs.get_max_idx_by_column(1)
            if idx < 0:
                idx = 0
            tabs.append(type=Tab.TAB_TOOL, tool_id=self.id, idx=idx, column_idx=1)
            tab = tabs.get_first_tab_by_tool(self.id)

        # Canvas is tab-only. Manual opening must reveal column 2 even
        # if an earlier automatic reveal was already consumed in this session.
        if tab is not None and tab.column_idx == 1 and not tabs.is_split_screen_enabled():
            tabs.enable_split_screen(update_switch=True)
        if tab is not None:
            tabs.switch_tab_by_idx(tab.idx, tab.column_idx)
        return tab

    def auto_open(self, load: bool = True):
        self.ensure_agent_surface()

    def ensure_agent_surface(self):
        """Ensure the single browser tab exists without stealing user focus.

        Agent/tool operations must never switch the active tab merely because the
        canvas runtime is being used.  The only automatic UI action allowed here
        is creating the missing singleton tab and revealing column 2 once per app
        session.  Manual Tools -> Canvas still uses ``open()`` and may
        explicitly focus the canvas tab.
        """
        self._ensure_surface()
        tabs = self.window.controller.tabs
        tab = tabs.get_first_tab_by_tool(self.id)

        if tab is not None and tab.column_idx != 1:
            # Respect a legacy/user-moved tab in the primary column.  Do not
            # focus it: model-side browser operations must not steal the chat
            # input focus or change the globally selected context.
            self.split_auto_expanded = True
            return "tab"

        first_reveal = bool(self._opt("auto_open_split", True)) and not self.split_auto_expanded
        if first_reveal:
            if not tabs.is_split_screen_enabled():
                tabs.enable_split_screen(update_switch=True)
            self.split_auto_expanded = True

        if tab is None:
            idx = self.window.core.tabs.get_max_idx_by_column(1)
            if idx < 0:
                idx = 0
            tabs.append(type=Tab.TAB_TOOL, tool_id=self.id, idx=idx, column_idx=1)
        # Important: if the tab already exists, leave both column focus and the
        # selected tab untouched.  The persistent runtime can render/update in
        # the background and the user keeps typing in Chat uninterrupted.
        return "tab"

    def close(self):
        """Hide/close the Canvas tab UI while preserving browser runtime."""
        return self.close_surface()

    def toggle(self):
        # The Tools menu is an opener/focuser, not a dialog toggle. Repeated
        # activation always reuses the canonical singleton tab.
        return self.open()

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = "txt"):
        """Keep the legacy Web Browser save hook available for UI compatibility."""
        if type == "html":
            text = output_clean_html(text)
        else:
            text = output_html2text(text)
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text, type))

    def show_hide(self, show: bool = True):
        if show:
            self.open()
        else:
            self.close()

    def get_toolbar_icon(self) -> QWidget:
        return self.window.ui.nodes["icon.web_browser"]

    def toggle_icon(self, state: bool):
        self.get_toolbar_icon().setVisible(state)

    def setup_menu(self) -> Dict[str, QAction]:
        actions = {}
        actions["web_browser"] = QAction(
            QIcon(":/icons/grid.svg"),
            trans("menu.tools.canvas_html"),
            self.window,
            checkable=False,
        )
        actions["web_browser"].triggered.connect(lambda: self.open())
        return actions

    def get_lang_mappings(self) -> Dict[str, Dict]:
        return {
            "menu.text": {
                "tools.web_browser": "menu.tools.canvas_html",
            }
        }

    def close_surface(self):
        tab = self.window.controller.tabs.get_first_tab_by_tool(self.id)
        if tab is None:
            self.detach_surface()
            return {"closed": "none", "session_alive": True}
        tabs = self.window.controller.tabs
        if tab.column_idx == 1 and tabs.is_split_screen_enabled():
            tabs.disable_split_screen()
            return {"closed": "split_screen", "session_alive": True}
        tabs.close(tab.idx, tab.column_idx)
        return {"closed": "tab", "session_alive": True}

    def as_tab(self, tab: Tab) -> QWidget:
        tool = Tool(window=self.window, tool=self, surface_kind="tab")
        tool_widget = tool.as_tab()
        widget = TabWidget()
        widget.from_tool(tool_widget)
        widget.setup()
        tool.set_tab(tab)
        return widget

    def setup_dialogs(self):
        # Canvas is intentionally tab-only. Do not register a dialog
        # frontend; the runtime itself may continue living in the hidden host.
        self.dialog = None

    def setup_theme(self):
        # Never touch user/model content on a theme change. Only the synthetic
        # empty Canvas page is regenerated so a live theme/profile switch cannot
        # leave a bright light grid inside the dark application theme.
        if self.surface is not None and self.blank_canvas_active:
            self._render_blank_canvas()

    def show_source(self):
        """Switch the persistent viewport to editable serialized page source.

        QWebEngine serialization is asynchronous on purpose. Running a nested
        event loop from inside the WebEngine context menu can leave the menu
        active while Chromium waits for the GUI loop, which made Show source
        appear to do nothing on some platforms.
        """
        self._ensure_surface()
        current = str(self.current_url() or "")
        current_qurl = QUrl(current)
        url = current if current_qurl.scheme() in ("http", "https", "file") else str(self.base_url or "")
        if self.backend == "playwright":
            self._ensure_playwright()
            html = str(self.pw_page.evaluate(self.JS_SERIALIZE_HTML) or self.runtime_html or "")
            self.surface.show_source(html, base_url=url)
            return

        page = self.surface.web.page()

        def ready(html):
            if self.surface is None:
                return
            text = str(html or self.runtime_html or "")
            self.surface.show_source(text, base_url=url)

        page.runJavaScript(self.JS_SERIALIZE_HTML, 0, ready)

    def show_canvas(self):
        """Return from source editor to the rendered Canvas/HTML viewport."""
        if self.surface is not None:
            self.surface.show_canvas()

    def apply_source_html(self, html: str, base_url: str = ""):
        """Apply an edit from source view to the same browser runtime."""
        params = {
            "html": str(html or ""),
            "base_url": base_url or self.base_url or "",
            "__ui": True,
            "__source_edit": True,
        }
        result = self._cmd_set_html(params)
        self._notify_state()
        return result

    # ------------------------------------------------------------------
    # Main-thread runtime API
    # ------------------------------------------------------------------

    def runtime_call(self, cmd: str, params: dict, plugin=None):
        # Keep old internal calls/conversation tool calls functional after the
        # public API rename; only canvas_* names are exposed to the model.
        if isinstance(cmd, str) and cmd.startswith("web_browser_"):
            cmd = "canvas_" + cmd[len("web_browser_"):]
        params = dict(params or {})
        params.setdefault("__agent", plugin is not None and not params.get("__ui"))
        self._ensure_surface()
        # Playwright is opt-in. If the user disables the master switch while a
        # sandbox session exists, the next operation cleanly returns to QWebEngine.
        if not self._sandbox_enabled() and self.backend == "playwright":
            self._set_backend("qt")
        handlers = {
            "canvas_open": self._cmd_open,
            "canvas_change_resolution": self._cmd_resolution,
            "canvas_set_html": self._cmd_set_html,
            "canvas_get_html": self._cmd_get_html,
            "canvas_current": lambda p: self.current_state(),
            "canvas_close": lambda p: self.close_surface(),
            "canvas_prev": self._cmd_prev,
            "canvas_next": self._cmd_next,
            "canvas_reload": self._cmd_reload,
            "canvas_screenshot": self._cmd_screenshot,
            "canvas_inspect": self._cmd_inspect,
            "canvas_click": self._cmd_click,
            "canvas_hover": self._cmd_hover,
            "canvas_type": self._cmd_type,
            "canvas_key": self._cmd_key,
            "canvas_scroll": self._cmd_scroll,
            "canvas_drag": self._cmd_drag,
            "canvas_wait": self._cmd_wait,
            "canvas_eval": self._cmd_eval,
            "canvas_select": self._cmd_select,
            "canvas_check": self._cmd_check,
            "canvas_upload": self._cmd_upload,
            "canvas_console": self._cmd_console,
            "canvas_annotations": self._cmd_annotations,
            "canvas_clear_annotations": lambda p: self._clear_annotations(),
            "web_server_start": self._cmd_server_start,
            "web_server_current": lambda p: self.server_state(),
            "web_server_stop": lambda p: self._cmd_server_stop(),
        }
        handler = handlers.get(cmd)
        if handler is None:
            raise ValueError(f"Unsupported Canvas/Web Browser command: {cmd}")
        result = handler(params)
        self._notify_state()
        return result

    def _cmd_open(self, p):
        self.ensure_agent_surface()
        sandbox_arg = p.get("sandbox")
        sandbox_enabled = self._sandbox_enabled()
        if not sandbox_enabled:
            # Master switch OFF: never import/start Playwright, regardless of what
            # the model requested. This keeps the built-in QWebEngine path silent.
            sandbox = False
            lock_agent_backend = False
        else:
            sandbox = sandbox_arg
            if sandbox is None:
                sandbox = self.backend == "playwright" if p.get("__ui") else True
            lock_agent_backend = bool(p.get("__agent") and sandbox_arg is not None)
        resolution = p.get("resolution")
        if resolution:
            width, height = self._parse_resolution(resolution)
            self._set_resolution(width, height, "auto")
            if p.get("__agent"):
                self.model_resolution = (self.width, self.height)
                # The model owns the viewport for the duration of BUSY. Once it
                # becomes IDLE, re-apply the visible UI fit (or hidden fallback).
                self.viewport_policy_timer.start(120)
        mode = "playwright" if bool(sandbox) else "qt"
        self._set_backend(mode)
        if p.get("__agent"):
            self.agent_backend_locked = lock_agent_backend
        url = self._resolve_url(str(p.get("url") or ""), p.get("__workdir"))
        if not url:
            url = self.virtual_url or "about:blank"
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.goto(url, wait_until="domcontentloaded")
            if url == "about:blank":
                self._render_blank_canvas()
            else:
                self.blank_canvas_active = False
                self.virtual_url = self.pw_page.url
                self._refresh_playwright_frame()
        else:
            if url == "about:blank":
                self._render_blank_canvas()
            else:
                self.blank_canvas_active = False
                self.surface.web.setUrl(QUrl.fromUserInput(url))
                self.virtual_url = url
        return self.current_state()

    def _cmd_resolution(self, p):
        width = int(p.get("width") or self.width)
        height = int(p.get("height") or self.height)
        orientation = str(p.get("orientation") or "auto").lower()
        self._set_resolution(width, height, orientation)
        if p.get("__agent"):
            self.model_resolution = (self.width, self.height)
            self.viewport_policy_timer.start(120)
        return self.current_state()

    def _cmd_set_html(self, p):
        self.ensure_agent_surface()
        if (self._sandbox_enabled() and p.get("__agent")
                and not self.agent_backend_locked and self.backend != "playwright"):
            self._set_backend("playwright")
        html = str(p.get("html") or "")
        workdir = p.get("__workdir") or os.getcwd()
        base_url = self._normalize_base_url(p.get("base_url"), workdir)
        runtime_base = base_url
        self.base_url = base_url
        if self.backend == "playwright":
            self._ensure_playwright()
            self.blank_canvas_active = False
            qbase = QUrl(base_url) if base_url else QUrl()
            if qbase.isLocalFile():
                server_root = qbase.toLocalFile()
                if os.path.isfile(server_root):
                    server_root = os.path.dirname(server_root)
                self._start_server(server_root, 0)
                runtime_base = self.server_url
            else:
                # Even with a remote <base>, serve the runtime document itself from
                # loopback so reload/history have a real URL and not about:blank.
                self._start_server(workdir, 0)
            self.base_url = runtime_base
            self.runtime_html = self._inject_base(html, runtime_base)
            runtime_url = urljoin(self.server_url, _PreviewHandler.RUNTIME_PATH.lstrip("/"))
            self.pw_page.goto(runtime_url, wait_until="domcontentloaded")
            self.virtual_url = self.pw_page.url
            self._refresh_playwright_frame()
        else:
            self.blank_canvas_active = False
            self.runtime_html = html
            self.surface.web.setHtml(html, QUrl(runtime_base) if runtime_base else QUrl.fromLocalFile(str(Path(workdir).resolve()) + os.sep))
            self.virtual_url = runtime_base or "about:blank"
        return {"url": self.current_url(), "base_url": self.base_url, "backend": self.backend, "ok": True}

    def _cmd_get_html(self, p):
        html = self._eval(self.JS_SERIALIZE_HTML)
        return {"url": self.current_url(), "html": html or ""}

    def _cmd_prev(self, p):
        if self.backend == "playwright":
            self._ensure_playwright()
            if self.pw_history_index > 0:
                self.pw_history_mode = "back"
                before = self.pw_page.url
                self.pw_page.go_back(wait_until="domcontentloaded")
                if self.pw_history_mode == "back" or self.pw_page.url == before:
                    self.pw_history_mode = None
                self._refresh_playwright_frame()
        else:
            self.surface.web.back()
        return self.current_state()

    def _cmd_next(self, p):
        if self.backend == "playwright":
            self._ensure_playwright()
            if self.pw_history_index + 1 < len(self.pw_history):
                self.pw_history_mode = "forward"
                before = self.pw_page.url
                self.pw_page.go_forward(wait_until="domcontentloaded")
                if self.pw_history_mode == "forward" or self.pw_page.url == before:
                    self.pw_history_mode = None
                self._refresh_playwright_frame()
        else:
            self.surface.web.forward()
        return self.current_state()

    def _cmd_reload(self, p):
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_history_mode = "reload"
            self.pw_page.reload(wait_until="domcontentloaded")
            self.pw_history_mode = None
            self._refresh_playwright_frame()
        else:
            self.surface.web.reload()
        return self.current_state()

    def _cmd_screenshot(self, p):
        path = p.get("path")
        if not path:
            tmp = self.window.core.config.get_user_dir("tmp")
            os.makedirs(tmp, exist_ok=True)
            path = os.path.join(tmp, f"canvas_{uuid.uuid4().hex}.png")
        path = os.path.abspath(str(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if self.backend == "playwright":
            self._ensure_playwright()
            full_page = bool(p.get("full_page", False))
            self.pw_page.screenshot(path=path, full_page=full_page)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                cursor_y = self.cursor_y
                if full_page:
                    try:
                        cursor_y += int(self.pw_page.evaluate("window.scrollY || 0") or 0)
                    except Exception:
                        pass
                self._draw_cursor_on_pixmap(pixmap, self.cursor_x, cursor_y)
                pixmap.save(path, "PNG")
        else:
            pixmap = self.surface.web.grab()
            self._draw_cursor_on_pixmap(pixmap)
            if not pixmap.save(path, "PNG"):
                raise RuntimeError("Could not save browser screenshot")
        return {"path": path, "url": self.current_url(), "width": self.width, "height": self.height, "backend": self.backend}

    def _cmd_inspect(self, p):
        selector = p.get("selector")
        limit = max(1, min(int(p.get("limit") or 100), 500))
        script = self.JS_INSPECT % (json.dumps(selector) if selector else "null", limit)
        result = self._eval(script)
        return {"url": self.current_url(), "elements": result or []}

    def _cmd_click(self, p):
        selector = p.get("selector")
        button = str(p.get("button") or "left")
        count = max(1, int(p.get("count") or 1))
        if self.backend == "playwright":
            self._ensure_playwright()
            if selector:
                locator = self.pw_page.locator(str(selector)).first
                box = locator.bounding_box()
                locator.click(button=button, click_count=count)
                if box:
                    self.cursor_x = int(box["x"] + box["width"] / 2)
                    self.cursor_y = int(box["y"] + box["height"] / 2)
            else:
                x, y = self._point(p)
                self.pw_page.mouse.click(x, y, button=button, click_count=count)
                self.cursor_x, self.cursor_y = x, y
            self._refresh_playwright_frame()
        else:
            if selector:
                script = f"""(() => {{ const e=document.querySelector({json.dumps(str(selector))}); if(!e) return false; const r=e.getBoundingClientRect(); e.focus(); e.click(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}; }})()"""
                pos = self._qt_js(script)
                if not pos:
                    raise RuntimeError(f"Element not found: {selector}")
                self.cursor_x, self.cursor_y = int(pos["x"]), int(pos["y"])
            else:
                x, y = self._point(p)
                self.cursor_x, self.cursor_y = x, y
                self._qt_js(self._js_mouse_event(x, y, "click", button, count))
            self._update_qt_virtual_cursor()
        return self.current_state()

    def _cmd_hover(self, p):
        selector = p.get("selector")
        if selector:
            script = f"""(() => {{ const e=document.querySelector({json.dumps(str(selector))}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}; }})()"""
            pos = self._eval(script)
            if not pos:
                raise RuntimeError(f"Element not found: {selector}")
            x, y = int(pos["x"]), int(pos["y"])
        else:
            x, y = self._point(p)
        self.cursor_x, self.cursor_y = x, y
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.mouse.move(x, y)
            self._refresh_playwright_frame()
        else:
            self._qt_js(self._js_mouse_event(x, y, "mousemove", "left", 0))
            self._update_qt_virtual_cursor()
        return self.current_state()

    def _cmd_type(self, p):
        selector = p.get("selector")
        text = str(p.get("text") or "")
        clear = bool(p.get("clear", False))
        enter = bool(p.get("press_enter", False))
        if self.backend == "playwright":
            self._ensure_playwright()
            target = self.pw_page.locator(str(selector)).first if selector else self.pw_page.locator(":focus")
            if selector:
                target.focus()
            if clear:
                target.fill("")
            target.type(text)
            if enter:
                target.press("Enter")
            self._refresh_playwright_frame()
        else:
            script = self._js_type(selector, text, clear, enter)
            ok = self._qt_js(script)
            if not ok:
                raise RuntimeError("No editable element is focused/found")
        return self.current_state()

    def _cmd_key(self, p):
        key = str(p.get("key") or "")
        if not key:
            raise ValueError("key is required")
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.keyboard.press(key)
            self._refresh_playwright_frame()
        else:
            self._qt_js(self._js_key(key))
        return self.current_state()

    def _cmd_scroll(self, p):
        dx = int(p.get("dx") or 0)
        dy = int(p.get("dy") or 0)
        if p.get("x") is not None and p.get("y") is not None:
            self.cursor_x, self.cursor_y = self._point(p)
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.mouse.move(self.cursor_x, self.cursor_y)
            self.pw_page.mouse.wheel(dx, dy)
            self._refresh_playwright_frame()
        else:
            self._qt_js(f"window.scrollBy({dx}, {dy}); true")
            self._update_qt_virtual_cursor()
        return self.current_state()

    def _cmd_drag(self, p):
        x1, y1 = self._clamp(int(p.get("x1")), int(p.get("y1")))
        x2, y2 = self._clamp(int(p.get("x2")), int(p.get("y2")))
        if self.backend == "playwright":
            self._ensure_playwright()
            self.pw_page.mouse.move(x1, y1)
            self.pw_page.mouse.down()
            self.pw_page.mouse.move(x2, y2, steps=12)
            self.pw_page.mouse.up()
            self._refresh_playwright_frame()
        else:
            script = f"""(() => {{
const a=document.elementFromPoint({x1},{y1}); const b=document.elementFromPoint({x2},{y2}); if(!a) return false;
for (const [t,x,y,buttons] of [['mousedown',{x1},{y1},1],['mousemove',{x2},{y2},1],['mouseup',{x2},{y2},0]]) {{
 const el=document.elementFromPoint(x,y)||a; el.dispatchEvent(new MouseEvent(t,{{bubbles:true,cancelable:true,clientX:x,clientY:y,buttons}}));
}} return true; }})()"""
            self._qt_js(script)
        self.cursor_x, self.cursor_y = x2, y2
        self._update_qt_virtual_cursor()
        return self.current_state()

    def _cmd_wait(self, p):
        selector = p.get("selector")
        timeout = max(0.1, min(float(p.get("timeout") or 10.0), 60.0))
        if selector:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self.backend == "playwright":
                    self._ensure_playwright()
                    if self.pw_page.locator(str(selector)).count() > 0:
                        self._refresh_playwright_frame()
                        return self.current_state()
                elif self._qt_js(f"!!document.querySelector({json.dumps(str(selector))})"):
                    return self.current_state()
                # Keep the Qt event loop responsive while an agent waits for the DOM.
                self._qt_delay(0.1)
            raise TimeoutError(f"Selector not found: {selector}")
        seconds = max(0.0, min(float(p.get("seconds") or 1.0), 30.0))
        self._qt_delay(seconds)
        if self.backend == "playwright":
            self._refresh_playwright_frame()
        return self.current_state()

    def _cmd_eval(self, p):
        javascript = str(p.get("javascript") or "")
        if not javascript:
            raise ValueError("javascript is required")
        return {"url": self.current_url(), "result": self._eval(javascript)}

    def _cmd_select(self, p):
        selector = str(p.get("selector") or "").strip()
        if not selector:
            raise ValueError("selector is required")
        value = p.get("value")
        label = p.get("label")
        index = p.get("index")
        if value is None and label is None and index is None:
            raise ValueError("value, label or index is required")
        if self.backend == "playwright":
            self._ensure_playwright()
            kwargs = {}
            if value is not None:
                kwargs["value"] = str(value)
            elif label is not None:
                kwargs["label"] = str(label)
            else:
                kwargs["index"] = int(index)
            selected = self.pw_page.locator(selector).first.select_option(**kwargs)
            self._refresh_playwright_frame()
            return {"selector": selector, "selected": selected, "url": self.current_url()}
        script = f"""(() => {{
          const el=document.querySelector({json.dumps(selector)}); if(!el || el.tagName!=='SELECT') return null;
          let idx=-1; const opts=Array.from(el.options);
          const value={json.dumps(None if value is None else str(value))};
          const label={json.dumps(None if label is None else str(label))};
          const wantedIndex={json.dumps(None if index is None else int(index))};
          if(value!==null) idx=opts.findIndex(o=>o.value===value);
          else if(label!==null) idx=opts.findIndex(o=>o.text===label || o.label===label);
          else idx=wantedIndex;
          if(idx<0 || idx>=opts.length) return null; el.selectedIndex=idx;
          el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}}));
          return {{value:el.value,label:opts[idx].text,index:idx}};
        }})()"""
        result = self._qt_js(script)
        if result is None:
            raise RuntimeError("Select element/option not found")
        return {"selector": selector, "selected": result, "url": self.current_url()}

    def _cmd_check(self, p):
        selector = str(p.get("selector") or "").strip()
        if not selector:
            raise ValueError("selector is required")
        checked = True if p.get("checked") is None else bool(p.get("checked"))
        if self.backend == "playwright":
            self._ensure_playwright()
            locator = self.pw_page.locator(selector).first
            if checked:
                locator.check()
            else:
                locator.uncheck()
            self._refresh_playwright_frame()
        else:
            script = f"""(() => {{ const e=document.querySelector({json.dumps(selector)}); if(!e || !('checked' in e)) return false;
            e.checked={str(checked).lower()}; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); return true; }})()"""
            if not self._qt_js(script):
                raise RuntimeError("Checkable element not found")
        return {"selector": selector, "checked": checked, "url": self.current_url()}

    def _cmd_upload(self, p):
        if self.backend != "playwright":
            raise RuntimeError("canvas_upload requires sandbox=true / Playwright backend")
        selector = str(p.get("selector") or "").strip()
        path = str(p.get("path") or "").strip()
        if not selector or not path:
            raise ValueError("selector and path are required")
        self._ensure_playwright()
        self.pw_page.locator(selector).first.set_input_files(path)
        self._refresh_playwright_frame()
        return {"selector": selector, "path": path, "url": self.current_url()}

    def _cmd_console(self, p):
        limit = max(1, min(int(p.get("limit") or 100), 1000))
        result = list(self.console[-limit:])
        if p.get("clear"):
            self.console.clear()
        return {"entries": result, "count": len(result)}

    def _cmd_annotations(self, p):
        result = list(self.annotations)
        if p.get("clear"):
            self.annotations.clear()
            self._render_annotations()
        return {"annotations": result, "count": len(result)}

    def _clear_annotations(self):
        count = len(self.annotations)
        self.annotations.clear()
        self._render_annotations()
        return {"cleared": count}

    # ------------------------------------------------------------------
    # Preview HTTP server
    # ------------------------------------------------------------------

    def _cmd_server_start(self, p):
        root = p.get("path") or p.get("__workdir") or os.getcwd()
        port = int(p.get("port") or 0)
        self._start_server(root, port)
        result = self.server_state()
        if p.get("open"):
            sandbox = True if p.get("sandbox") is None else bool(p.get("sandbox"))
            self._cmd_open({
                "url": self.server_url,
                "sandbox": sandbox,
                "__workdir": self.server_root,
                "__agent": bool(p.get("__agent")),
            })
            result["browser"] = self.current_state()
        return result

    def _start_server(self, root, port=0):
        root = os.path.realpath(os.path.abspath(os.path.expanduser(str(root))))
        if not os.path.isdir(root):
            raise NotADirectoryError(root)
        port = int(port or 0)
        if self.server is not None and self.server_root == root:
            current_port = int(self.server.server_address[1])
            if port in (0, current_port):
                return self.server_url
        self._stop_server()
        handler = partial(
            _PreviewHandler,
            directory=root,
            runtime_html_getter=lambda: self.runtime_html,
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self.server.daemon_threads = True
        actual_port = int(self.server.server_address[1])
        self.server_root = root
        self.server_url = f"http://127.0.0.1:{actual_port}/"
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="PyGPT-WebPreview")
        self.server_thread.start()
        return self.server_url

    def _cmd_server_stop(self):
        old = self.server_state()
        self._stop_server()
        old["running"] = False
        return old

    def _stop_server(self):
        server = self.server
        self.server = None
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        self.server_thread = None
        self.server_root = None
        self.server_url = None

    def server_state(self):
        return {"running": self.server is not None, "root": self.server_root, "url": self.server_url}

    # ------------------------------------------------------------------
    # Playwright backend
    # ------------------------------------------------------------------

    def _set_backend(self, mode: str):
        mode = "playwright" if mode == "playwright" else "qt"
        if self.backend == mode:
            self.surface.set_mode(mode)
            if mode == "playwright":
                self._ensure_playwright()
            return
        previous = self.backend
        if mode == "playwright":
            try:
                self._ensure_playwright()
            except Exception:
                self.backend = previous
                self.surface.set_mode(previous)
                raise
        elif self.pw_page is not None:
            self._stop_playwright()
        self.backend = mode
        self.surface.set_mode(mode)
        self._notify_state()

    def _ensure_playwright(self):
        if self.pw_page is not None:
            try:
                _ = self.pw_page.url
                return
            except Exception:
                self._stop_playwright()
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is required for sandbox=true. Install it and a browser, e.g. `pip install playwright && playwright install chromium`.") from exc
        path = str(self._opt("playwright_path", "") or "").strip()
        engine = str(self._opt("playwright_engine", "chromium") or "chromium")
        if path:
            path = os.path.abspath(os.path.expanduser(path))
            if not os.path.isdir(path):
                raise RuntimeError(
                    f"Playwright browsers path does not exist: {path}. Install the browser with "
                    f"`playwright install {engine}` and configure the browsers directory."
                )
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = path
        elif os.environ.get("APPIMAGE"):
            raise RuntimeError(
                "Playwright browsers directory is required in AppImage mode. Install the browser on the host "
                f"with `playwright install {engine}` and set it in Canvas plugin settings."
            )
        args = [x.strip() for x in str(self._opt("playwright_args", "") or "").split(",") if x.strip()]
        try:
            self.pw = sync_playwright().start()
            launcher = getattr(self.pw, engine)
            kwargs = {"headless": True}
            if args and engine == "chromium":
                kwargs["args"] = args
            self.pw_browser = launcher.launch(**kwargs)
            self.pw_context = self.pw_browser.new_context(viewport={"width": self.width, "height": self.height})
            self.pw_page = self.pw_context.new_page()
            self.pw_page.expose_binding("__pygpt_remove_annotation", self._playwright_remove_annotation_binding)
            self.pw_page.expose_binding("__pygpt_add_annotation", self._playwright_add_annotation_binding)
            self.pw_page.on("console", lambda msg: self._append_console("console", getattr(msg, "type", "log"), getattr(msg, "text", "")))
            self.pw_page.on("pageerror", lambda exc: self._append_console("pageerror", "error", str(exc)))
            self.pw_page.goto("about:blank")
            self.pw_page.set_content(self._blank_canvas_html(), wait_until="domcontentloaded")
            self.blank_canvas_active = True
            self.virtual_url = "about:blank"
            self.pw_page.on("framenavigated", self._on_playwright_navigated)
            if self.pw_frame_timer is not None and not self.pw_frame_timer.isActive():
                self.pw_frame_timer.start()
            self._refresh_playwright_frame()
        except Exception:
            self._stop_playwright()
            raise

    def _stop_playwright(self):
        if self.pw_frame_timer is not None:
            self.pw_frame_timer.stop()
        for obj, method in ((self.pw_page, "close"), (self.pw_context, "close"), (self.pw_browser, "close"), (self.pw, "stop")):
            if obj is not None:
                try:
                    getattr(obj, method)()
                except Exception:
                    pass
        self.pw_page = None
        self.pw_context = None
        self.pw_browser = None
        self.pw = None
        self.pw_history = []
        self.pw_history_index = -1
        self.pw_history_mode = None

    def _on_playwright_navigated(self, frame):
        if self.pw_page is None:
            return
        try:
            if frame != self.pw_page.main_frame:
                return
            url = str(frame.url or "")
        except Exception:
            return
        if not url:
            return
        mode = self.pw_history_mode
        if mode == "back":
            if self.pw_history_index > 0:
                self.pw_history_index -= 1
            if 0 <= self.pw_history_index < len(self.pw_history):
                self.pw_history[self.pw_history_index] = url
            self.pw_history_mode = None
        elif mode == "forward":
            if self.pw_history_index + 1 < len(self.pw_history):
                self.pw_history_index += 1
            if 0 <= self.pw_history_index < len(self.pw_history):
                self.pw_history[self.pw_history_index] = url
            self.pw_history_mode = None
        elif mode == "reload":
            if 0 <= self.pw_history_index < len(self.pw_history):
                self.pw_history[self.pw_history_index] = url
        else:
            current = self.pw_history[self.pw_history_index] if 0 <= self.pw_history_index < len(self.pw_history) else None
            if current != url:
                self.pw_history = self.pw_history[:self.pw_history_index + 1]
                self.pw_history.append(url)
                self.pw_history_index = len(self.pw_history) - 1
        if url != "about:blank":
            self.virtual_url = url
        # Avoid nested Playwright sync calls (e.g. title/evaluate) from inside a
        # Playwright event callback. Restore overlays and publish state on the
        # next Qt turn instead.
        QTimer.singleShot(0, self._restore_annotations_after_navigation)
        QTimer.singleShot(0, self._notify_state)

    def _restore_annotations_after_navigation(self):
        try:
            self._render_annotations()
            if self.backend == "playwright" and self.pw_page is not None:
                self._schedule_playwright_frame(10)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass

    def _refresh_playwright_frame(self):
        self.pw_frame_pending = False
        if self.pw_page is None:
            return
        data = self.pw_page.screenshot(type="png")
        self.surface.sandbox.set_frame(data)
        page_url = self.pw_page.url
        if page_url and page_url != "about:blank":
            self.virtual_url = page_url
        self.surface.sandbox.update()
        self._notify_state()

    def _poll_playwright_frame(self):
        """Refresh the remote framebuffer while it is actually visible to the user."""
        if self.backend != "playwright" or self.pw_page is None or self.surface_owner is None:
            return
        scroll = getattr(self.surface_owner, "scroll", None)
        if scroll is not None and not scroll.isVisible():
            return
        try:
            data = self.pw_page.screenshot(type="png")
            self.surface.sandbox.set_frame(data)
            page_url = self.pw_page.url
            if page_url and page_url != "about:blank":
                self.virtual_url = page_url
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass

    def _schedule_playwright_frame(self, delay_ms: int = 70):
        if self.pw_frame_pending or self.pw_page is None:
            return
        self.pw_frame_pending = True
        QTimer.singleShot(max(0, int(delay_ms)), self._refresh_playwright_frame)

    def user_playwright_action(self, op: str, p: dict):
        if self.backend != "playwright":
            return
        try:
            self._ensure_playwright()
            if op == "hover":
                x, y = self._clamp(int(p["x"]), int(p["y"]))
                self.pw_page.mouse.move(x, y)
            elif op == "mouse_down":
                x, y = self._clamp(int(p["x"]), int(p["y"]))
                self.pw_page.mouse.move(x, y)
                self.pw_page.mouse.down(button=p.get("button", "left"))
            elif op == "mouse_up":
                x, y = self._clamp(int(p["x"]), int(p["y"]))
                self.pw_page.mouse.move(x, y)
                self.pw_page.mouse.up(button=p.get("button", "left"))
            elif op == "click":
                self.pw_page.mouse.click(int(p["x"]), int(p["y"]), click_count=int(p.get("count", 1)))
            elif op == "scroll":
                self.pw_page.mouse.wheel(int(p.get("dx", 0)), int(p.get("dy", 0)))
            elif op == "type_raw":
                self.pw_page.keyboard.type(str(p.get("text", "")))
            elif op == "key":
                self.pw_page.keyboard.press(str(p.get("key") or ""))
            if op == "hover":
                self._schedule_playwright_frame()
            else:
                self._refresh_playwright_frame()
        except Exception as exc:
            self.window.core.debug.log(exc)

    # ------------------------------------------------------------------
    # Qt WebEngine helpers
    # ------------------------------------------------------------------

    def _qt_js(self, script: str, timeout_ms: int = 10000):
        loop = QEventLoop()
        box = {"done": False, "value": None}

        def callback(value):
            box["done"] = True
            box["value"] = value
            if loop.isRunning():
                loop.quit()

        self.surface.web.page().runJavaScript(script, 0, callback)
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()
        if not box["done"]:
            raise TimeoutError("WebEngine JavaScript operation timed out")
        return box["value"]

    def _qt_html(self):
        loop = QEventLoop()
        box = {"done": False, "value": ""}

        def callback(value):
            box["done"] = True
            box["value"] = value or ""
            if loop.isRunning():
                loop.quit()

        self.surface.web.page().toHtml(callback)
        QTimer.singleShot(10000, loop.quit)
        loop.exec()
        if not box["done"]:
            raise TimeoutError("WebEngine HTML serialization timed out")
        return box["value"]

    def _qt_delay(self, seconds):
        loop = QEventLoop()
        QTimer.singleShot(max(0, int(float(seconds) * 1000)), loop.quit)
        loop.exec()

    def on_qt_load_finished(self, success: bool):
        self.virtual_url = self.surface.web.url().toString() or self.virtual_url
        self._update_qt_virtual_cursor()
        self._render_annotations()
        self._notify_state()

    def _update_qt_virtual_cursor(self):
        if self.backend != "qt":
            return
        x, y = self.cursor_x, self.cursor_y
        script = f"""(() => {{
let c=document.getElementById('__pygpt_virtual_cursor');
if(!c){{c=document.createElement('div');c.id='__pygpt_virtual_cursor';Object.assign(c.style,{{position:'fixed',zIndex:'2147483647',width:'14px',height:'14px',border:'2px solid #ff2d55',borderRadius:'50%',pointerEvents:'none',boxSizing:'border-box'}});document.documentElement.appendChild(c);}}
c.style.left='{x-7}px'; c.style.top='{y-7}px'; return true; }})()"""
        try:
            self.surface.web.page().runJavaScript(script)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Shared helpers/state
    # ------------------------------------------------------------------

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
            "sandbox": self.backend == "playwright", "sandbox_enabled": self._sandbox_enabled(),
            "width": self.width, "height": self.height,
            "resolution": f"{self.width}x{self.height}", "orientation": self.orientation,
            "cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "base_url": self.base_url,
            "can_go_back": can_back, "can_go_forward": can_forward,
            "history_length": len(self.pw_history) if self.backend == "playwright" else None,
            "ui_surface": ui_surface, "session_alive": True,
            "server": self.server_state(), "annotations": len(self.annotations),
        }

    def _notify_state(self):
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

    def _set_resolution(self, width, height, orientation="auto", clamp_min: bool = True):
        min_width = 240 if clamp_min else 1
        min_height = 180 if clamp_min else 1
        width = max(min_width, min(int(width), 7680))
        height = max(min_height, min(int(height), 4320))
        orientation = str(orientation or "auto").lower()
        if orientation == "portrait" and width > height:
            width, height = height, width
        elif orientation == "landscape" and height > width:
            width, height = height, width
        if width == self.width and height == self.height:
            return False
        self.width, self.height = width, height
        self.orientation = "landscape" if width >= height else "portrait"
        self.surface.set_resolution(width, height)
        if self.pw_page is not None:
            self.pw_page.set_viewport_size({"width": width, "height": height})
            self._refresh_playwright_frame()
        self.cursor_x = min(self.cursor_x, width - 1)
        self.cursor_y = min(self.cursor_y, height - 1)
        self._update_qt_virtual_cursor()
        return True

    @staticmethod
    def _parse_resolution(value):
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return int(value[0]), int(value[1])
        text = str(value).lower().replace(" ", "")
        if "x" in text:
            a, b = text.split("x", 1)
            return int(a), int(b)
        raise ValueError("resolution must be WIDTHxHEIGHT or [width,height]")

    def _clamp(self, x, y):
        return max(0, min(self.width - 1, int(x))), max(0, min(self.height - 1, int(y)))

    def _point(self, p):
        if p.get("x") is None or p.get("y") is None:
            raise ValueError("x and y are required when selector is omitted")
        return self._clamp(int(p["x"]), int(p["y"]))

    def _resolve_url(self, value: str, workdir=None):
        value = (value or "").strip()
        if not value:
            return ""
        if self.server_url and not QUrl(value).scheme() and not os.path.isabs(value):
            local_candidate = os.path.join(self.server_root or "", value)
            if os.path.exists(local_candidate):
                return urljoin(self.server_url, value.replace(os.sep, "/"))
        path = Path(os.path.expanduser(value))
        if not path.is_absolute() and workdir:
            path = Path(workdir) / path
        if path.exists():
            return QUrl.fromLocalFile(str(path.resolve())).toString()
        qurl = QUrl.fromUserInput(value)
        return qurl.toString()

    @staticmethod
    def _normalize_base_url(base_url, workdir):
        if base_url:
            text = str(base_url).strip()
            q = QUrl.fromUserInput(text)
            if q.scheme() in ("http", "https"):
                return q.toString()
            if q.isLocalFile():
                path = Path(q.toLocalFile()).expanduser()
            else:
                path = Path(text).expanduser()
                if not path.is_absolute():
                    path = Path(workdir) / path
        else:
            path = Path(workdir)
        path = path.resolve()
        if path.is_file():
            path = path.parent
        return QUrl.fromLocalFile(str(path) + os.sep).toString()

    @staticmethod
    def _inject_base(html, base_url):
        if not base_url or "<base" in html.lower():
            return html
        tag = f'<base href="{base_url}">'
        lower = html.lower()
        pos = lower.find("<head")
        if pos >= 0:
            end = html.find(">", pos)
            if end >= 0:
                return html[:end+1] + tag + html[end+1:]
        return tag + html

    def _eval(self, script):
        if self.backend == "playwright":
            self._ensure_playwright()
            try:
                result = self.pw_page.evaluate(script)
            except Exception as first_exc:
                # Playwright evaluate accepts expressions/functions. As a convenience,
                # also accept a plain JavaScript function body like Qt runJavaScript does.
                try:
                    result = self.pw_page.evaluate(f"() => {{ {script} }}")
                except Exception:
                    raise first_exc
            self._refresh_playwright_frame()
            return result
        return self._qt_js(script)

    @staticmethod
    def _js_mouse_event(x, y, event_type, button, count):
        button_map = {"left": 0, "middle": 1, "right": 2}
        btn = button_map.get(button, 0)
        return f"""(() => {{ const e=document.elementFromPoint({x},{y}); if(!e) return false;
e.dispatchEvent(new MouseEvent({json.dumps(event_type)},{{bubbles:true,cancelable:true,clientX:{x},clientY:{y},button:{btn},detail:{count}}}));
if({json.dumps(event_type)}==='click' && e.focus) e.focus(); return true; }})()"""

    @staticmethod
    def _js_type(selector, text, clear, enter):
        sel = json.dumps(str(selector)) if selector else "null"
        return f"""(() => {{
const e={sel} ? document.querySelector({sel}) : document.activeElement; if(!e) return false; e.focus();
const t={json.dumps(text)}; const clear={json.dumps(bool(clear))};
if ('value' in e) {{
  const proto = e.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto,'value')?.set;
  const next = clear ? t : String(e.value||'') + t;
  if(setter) setter.call(e,next); else e.value=next;
  e.dispatchEvent(new InputEvent('input',{{bubbles:true,inputType:'insertText',data:t}})); e.dispatchEvent(new Event('change',{{bubbles:true}}));
}} else if(e.isContentEditable) {{ if(clear)e.textContent=''; e.textContent += t; e.dispatchEvent(new InputEvent('input',{{bubbles:true,data:t}})); }}
if ({json.dumps(bool(enter))}) {{ e.dispatchEvent(new KeyboardEvent('keydown',{{key:'Enter',code:'Enter',bubbles:true}})); if(e.form && e.form.requestSubmit)e.form.requestSubmit(); e.dispatchEvent(new KeyboardEvent('keyup',{{key:'Enter',code:'Enter',bubbles:true}})); }}
return true; }})()"""

    @staticmethod
    def _js_key(key):
        raw = str(key)
        parts = raw.replace("Ctrl", "Control").split("+")
        main = parts[-1]
        mods = set(parts[:-1])
        ctrl = "Control" in mods
        alt = "Alt" in mods
        shift = "Shift" in mods
        meta = "Meta" in mods or "Command" in mods
        if ctrl and main.lower() == "a":
            action = "if('select' in e)e.select(); else document.execCommand('selectAll');"
        elif main == "Backspace":
            action = "if('value' in e){e.value=String(e.value||'').slice(0,-1);e.dispatchEvent(new Event('input',{bubbles:true}));}"
        elif main == "Tab":
            action = "const xs=[...document.querySelectorAll('a,button,input,textarea,select,[tabindex]')].filter(x=>!x.disabled&&x.tabIndex>=0); const i=xs.indexOf(e); if(xs.length)xs[(i+1)%xs.length].focus();"
        elif main == "Enter":
            action = "if(e.click && (e.tagName==='BUTTON'||e.tagName==='A'))e.click(); else if(e.form&&e.form.requestSubmit)e.form.requestSubmit();"
        else:
            action = ""
        return f"""(() => {{ const e=document.activeElement||document.body; const opts={{key:{json.dumps(main)},code:{json.dumps(main)},ctrlKey:{str(ctrl).lower()},altKey:{str(alt).lower()},shiftKey:{str(shift).lower()},metaKey:{str(meta).lower()},bubbles:true,cancelable:true}}; e.dispatchEvent(new KeyboardEvent('keydown',opts)); {action} e.dispatchEvent(new KeyboardEvent('keyup',opts)); return true; }})()"""

    def _draw_cursor_on_pixmap(self, pixmap, x=None, y=None):
        from PySide6.QtGui import QPainter, QPen
        if pixmap is None or pixmap.isNull():
            return
        painter = QPainter(pixmap)
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(2)
        painter.setPen(pen)
        x = int(self.cursor_x if x is None else x)
        y = int(self.cursor_y if y is None else y)
        painter.drawEllipse(x - 7, y - 7, 14, 14)
        painter.drawLine(x - 11, y, x + 11, y)
        painter.drawLine(x, y - 11, x, y + 11)
        painter.end()

    def append_qt_console(self, level, message, line_number=0, source_id=""):
        """Forward QWebEngine console output into the shared browser console buffer."""
        level_name = str(level).rsplit(".", 1)[-1]
        source = str(source_id or "qt-webengine")
        text = str(message)
        if line_number:
            text = f"{text} (line {int(line_number)})"
        self._append_console(source, level_name, text)

    def _append_console(self, source, level, message):
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

    def qt_key_to_playwright(self, event):
        key_map = {
            Qt.Key_Return: "Enter", Qt.Key_Enter: "Enter", Qt.Key_Escape: "Escape", Qt.Key_Tab: "Tab",
            Qt.Key_Backspace: "Backspace", Qt.Key_Delete: "Delete", Qt.Key_Left: "ArrowLeft",
            Qt.Key_Right: "ArrowRight", Qt.Key_Up: "ArrowUp", Qt.Key_Down: "ArrowDown",
            Qt.Key_Home: "Home", Qt.Key_End: "End", Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown",
        }
        base = key_map.get(event.key()) or event.text() or ""
        mods = []
        if event.modifiers() & Qt.ControlModifier: mods.append("Control")
        if event.modifiers() & Qt.AltModifier: mods.append("Alt")
        if event.modifiers() & Qt.ShiftModifier: mods.append("Shift")
        if event.modifiers() & Qt.MetaModifier: mods.append("Meta")
        return "+".join(mods + [base]) if base else "+".join(mods)

    # ------------------------------------------------------------------
    # User annotations
    # ------------------------------------------------------------------

    def get_selection_text(self, backend=None):
        backend = backend or self.backend
        script = "(() => (window.getSelection && window.getSelection().toString() || '').trim().slice(0, 4000))()"
        try:
            if backend == "playwright":
                self._ensure_playwright()
                return str(self.pw_page.evaluate(script) or "")
            return str(self._qt_js(script) or "")
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass
            return ""

    def annotate_selection(self, selected: str = "", position=None, backend=None):
        """Open the lightweight in-page annotation composer for current selection.

        QWebEngine JavaScript is deliberately asynchronous here. Context-menu
        actions run inside Chromium/Qt event handling, and nesting a QEventLoop
        while waiting for ``runJavaScript`` can stall for the full timeout.
        """
        x = int(position.x()) if position is not None else -1
        y = int(position.y()) if position is not None else -1
        self._show_annotation_editor(
            x=x,
            y=y,
            prefer_selection=True,
            selected_hint=str(selected or ""),
            backend=backend or self.backend,
        )

    def annotate_at(self, x: int, y: int, backend="qt"):
        """Open the in-page annotation composer for the element under (x, y)."""
        self._show_annotation_editor(
            x=int(x),
            y=int(y),
            prefer_selection=False,
            selected_hint="",
            backend=backend or self.backend,
        )

    def _show_annotation_editor(self, x: int, y: int, prefer_selection: bool, selected_hint: str, backend=None):
        backend = backend or self.backend
        script = self._annotation_editor_script(x, y, prefer_selection, selected_hint, backend)
        try:
            if backend == "playwright":
                self._ensure_playwright()
                self.pw_page.evaluate(script)
                self._schedule_playwright_frame(10)
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

    def _annotation_editor_script(self, x: int, y: int, prefer_selection: bool, selected_hint: str, backend: str):
        """Return JS for the fast, non-modal annotation editor rendered in-page."""
        script = r"""(() => {
          const backend = __BACKEND__;
          const px = __X__, py = __Y__;
          const preferSelection = __PREFER_SELECTION__;
          const selectedHint = __SELECTED_HINT__;
          const old = document.getElementById('__pygpt_annotation_editor');
          if (old) old.remove();

          const ensureRef = (el) => {
            if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
            let ref = el.getAttribute('data-pygpt-ref');
            if (!ref) {
              ref = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
              el.setAttribute('data-pygpt-ref', ref);
            }
            return ref;
          };
          const descriptorFor = (el, rect, selectionRect) => {
            if (!el) return {};
            const r = rect || el.getBoundingClientRect();
            const ref = ensureRef(el);
            const out = {
              tag: (el.tagName || '').toLowerCase(),
              id: el.id || '',
              className: String(el.className || ''),
              selector: ref ? '[data-pygpt-ref="' + ref + '"]' : '',
              text: (el.innerText || el.value || '').trim().slice(0, 500),
              x: Math.round(r.left || 0), y: Math.round(r.top || 0),
              width: Math.max(2, Math.round(r.width || 0)),
              height: Math.max(2, Math.round(r.height || 0))
            };
            if (selectionRect) out.selectionRect = selectionRect;
            return out;
          };

          let selection = '';
          let descriptor = {};
          let anchor = null;
          const sel = window.getSelection && window.getSelection();
          if (preferSelection && sel && sel.rangeCount > 0 && !sel.isCollapsed) {
            const range = sel.getRangeAt(0);
            const rr = range.getBoundingClientRect();
            let node = range.commonAncestorContainer;
            const el = node && node.nodeType === Node.ELEMENT_NODE ? node : node && node.parentElement;
            if (el && rr && (rr.width || rr.height)) {
              const tr = el.getBoundingClientRect();
              descriptor = descriptorFor(el, tr, {
                dx: Math.round(rr.left - tr.left), dy: Math.round(rr.top - tr.top),
                width: Math.max(2, Math.round(rr.width)), height: Math.max(2, Math.round(rr.height))
              });
              anchor = rr;
              selection = String(sel.toString() || selectedHint || '').trim().slice(0, 4000);
            }
          }
          if (!anchor) {
            const cx = px >= 0 ? px : Math.round(window.innerWidth / 2);
            const cy = py >= 0 ? py : Math.round(window.innerHeight / 2);
            const el = document.elementFromPoint(cx, cy) || document.body || document.documentElement;
            const r = el ? el.getBoundingClientRect() : {left:cx, top:cy, width:1, height:1, right:cx+1, bottom:cy+1};
            descriptor = descriptorFor(el, r, null);
            anchor = r;
            selection = String(selectedHint || '').trim().slice(0, 4000);
          }

          const editor = document.createElement('div');
          editor.id = '__pygpt_annotation_editor';
          editor.setAttribute('data-pygpt-ui', 'annotation-editor');
          Object.assign(editor.style, {
            position:'fixed', zIndex:'2147483647', width:'min(360px,calc(100vw - 20px))',
            boxSizing:'border-box', padding:'10px', background:'rgba(27,28,32,.98)',
            color:'#f7f7f8', border:'1px solid rgba(168,85,247,.9)', borderRadius:'10px',
            boxShadow:'0 12px 34px rgba(0,0,0,.38)', fontFamily:'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
            fontSize:'12px', lineHeight:'1.35', pointerEvents:'auto'
          });
          const title = document.createElement('div');
          title.textContent = selection ? __TITLE_SELECTION__ : __TITLE_ELEMENT__;
          Object.assign(title.style, {fontWeight:'700', color:'#d8b4fe', margin:'0 0 7px 1px'});
          const textarea = document.createElement('textarea');
          textarea.placeholder = selection ? __PROMPT_SELECTION__ : __PROMPT_ELEMENT__;
          textarea.rows = 4;
          Object.assign(textarea.style, {
            display:'block', width:'100%', minHeight:'82px', maxHeight:'220px', resize:'vertical',
            boxSizing:'border-box', padding:'8px 9px', border:'1px solid rgba(255,255,255,.18)',
            borderRadius:'7px', outline:'none', background:'#17181b', color:'#fff',
            font:'12px/1.4 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
          });
          const actions = document.createElement('div');
          Object.assign(actions.style, {display:'flex', justifyContent:'flex-end', gap:'7px', marginTop:'8px'});
          const button = (label, primary) => {
            const b = document.createElement('button');
            b.type = 'button'; b.textContent = label;
            Object.assign(b.style, {
              minWidth:'66px', height:'29px', padding:'0 10px', borderRadius:'6px', cursor:'pointer',
              border: primary ? '1px solid #8b5cf6' : '1px solid rgba(255,255,255,.18)',
              background: primary ? '#7c3aed' : '#2a2b30', color:'#fff', font:'600 12px system-ui,sans-serif'
            });
            return b;
          };
          const cancel = button(__CANCEL__, false);
          const add = button(__ADD__, true);
          actions.append(cancel, add);
          editor.append(title, textarea, actions);
          document.documentElement.appendChild(editor);

          const ew = Math.min(360, Math.max(240, window.innerWidth - 20));
          const eh = 178;
          let left = Math.max(10, Math.min(window.innerWidth - ew - 10, Number(anchor.left || 10)));
          let top = Number(anchor.bottom != null ? anchor.bottom : ((anchor.top || 10) + (anchor.height || 0))) + 10;
          if (top + eh > window.innerHeight - 10) top = Math.max(10, Number(anchor.top || 10) - eh - 10);
          editor.style.left = Math.round(left) + 'px';
          editor.style.top = Math.round(top) + 'px';

          const close = () => { if (editor.isConnected) editor.remove(); };
          cancel.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation(); close(); };
          const submit = () => {
            const payload = {selection, element:descriptor, note:String(textarea.value || '')};
            close();
            try {
              if (backend === 'playwright' && typeof window.__pygpt_add_annotation === 'function') {
                window.__pygpt_add_annotation(payload);
              } else {
                console.info('__PYGPT_ANNOTATION_ADD__:' + JSON.stringify(payload));
              }
            } catch (_) {}
          };
          add.onclick = (ev) => { ev.preventDefault(); ev.stopPropagation(); submit(); };
          textarea.addEventListener('keydown', (ev) => {
            if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') { ev.preventDefault(); submit(); }
            else if (ev.key === 'Escape') { ev.preventDefault(); close(); }
          });
          setTimeout(() => textarea.focus({preventScroll:true}), 0);
          return true;
        })()"""
        return script.replace('__BACKEND__', json.dumps(str(backend or 'qt'))) \
            .replace('__X__', str(int(x))) \
            .replace('__Y__', str(int(y))) \
            .replace('__PREFER_SELECTION__', 'true' if prefer_selection else 'false') \
            .replace('__SELECTED_HINT__', json.dumps(str(selected_hint or ''), ensure_ascii=False)) \
            .replace('__TITLE_SELECTION__', json.dumps(trans('ui.annotate_selection', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__TITLE_ELEMENT__', json.dumps(trans('ui.annotate_element', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__PROMPT_SELECTION__', json.dumps(trans('ui.annotation_selection_prompt', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__PROMPT_ELEMENT__', json.dumps(trans('ui.annotation_element_prompt', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__CANCEL__', json.dumps(trans('ui.cancel', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__ADD__', json.dumps(trans('ui.add', domain='plugin.canvas_web'), ensure_ascii=False))

    def _selection_descriptor(self, backend=None):
        script = r"""(() => {
          const sel = window.getSelection && window.getSelection();
          if (!sel || sel.rangeCount < 1 || sel.isCollapsed) return null;
          const range = sel.getRangeAt(0);
          const rr = range.getBoundingClientRect();
          let node = range.commonAncestorContainer;
          let el = node && node.nodeType === Node.ELEMENT_NODE ? node : node && node.parentElement;
          if (!el) return null;
          const tr = el.getBoundingClientRect();
          let ref = el.getAttribute('data-pygpt-ref');
          if (!ref) {
            ref = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
            el.setAttribute('data-pygpt-ref', ref);
          }
          return {
            tag: el.tagName.toLowerCase(), id: el.id || '', className: String(el.className || ''),
            selector: '[data-pygpt-ref="' + ref + '"]',
            text: (el.innerText || el.value || '').trim().slice(0, 500),
            x: Math.round(tr.x), y: Math.round(tr.y), width: Math.round(tr.width), height: Math.round(tr.height),
            selectionRect: {
              dx: Math.round(rr.x - tr.x), dy: Math.round(rr.y - tr.y),
              width: Math.max(2, Math.round(rr.width)), height: Math.max(2, Math.round(rr.height))
            }
          };
        })()"""
        if backend == "playwright":
            self._ensure_playwright()
            return self.pw_page.evaluate(script)
        return self._qt_js(script)

    def _element_at(self, x, y, backend):
        script = f"""(() => {{ const e=document.elementFromPoint({int(x)},{int(y)}); if(!e)return null; const r=e.getBoundingClientRect(); let ref=e.getAttribute('data-pygpt-ref'); if(!ref){{ref='a'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);e.setAttribute('data-pygpt-ref',ref);}} return {{tag:e.tagName.toLowerCase(),id:e.id||'',className:String(e.className||''),selector:'[data-pygpt-ref="'+ref+'"]',text:(e.innerText||e.value||'').trim().slice(0,500),outerHTML:e.outerHTML.slice(0,1500),selection:(window.getSelection()?.toString()||'').trim().slice(0,2000),x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}}; }})()"""
        if backend == "playwright":
            self._ensure_playwright()
            return self.pw_page.evaluate(script)
        return self._qt_js(script)

    def add_annotation(self, selection=None, element=None, note=""):
        self.annotation_seq += 1
        item = {
            "id": self.annotation_seq, "time": time.time(), "url": self.current_url(),
            "selection": selection or "", "element": element or {}, "note": str(note or ""),
        }
        self.annotations.append(item)
        max_items = max(1, int(self._opt("max_annotations", 30) or 30))
        if len(self.annotations) > max_items:
            del self.annotations[:-max_items]
        self._render_annotations()
        self.window.update_status(
            f"{trans('ui.annotation_added', domain='plugin.canvas_web')} #{self.annotation_seq}"
        )
        return item

    def _playwright_remove_annotation_binding(self, source, annotation_id):
        try:
            annotation_id = int(annotation_id)
        except Exception:
            return False
        # Binding callbacks run from Playwright. Defer mutation/rendering to the
        # Qt turn so no nested Playwright call is made inside the callback.
        QTimer.singleShot(0, lambda aid=annotation_id: self._remove_annotation(aid))
        return True

    def _playwright_add_annotation_binding(self, source, payload):
        if not isinstance(payload, dict):
            return False
        data = {
            "selection": str(payload.get("selection") or ""),
            "element": payload.get("element") if isinstance(payload.get("element"), dict) else {},
            "note": str(payload.get("note") or ""),
        }
        QTimer.singleShot(0, lambda item=data: self.add_annotation(
            selection=item["selection"], element=item["element"], note=item["note"]
        ))
        return True

    def handle_annotation_console(self, message):
        """Consume private QWebEngine JS bridge messages for annotation UI."""
        text = str(message or "")
        remove_prefix = "__PYGPT_ANNOTATION_REMOVE__:"
        add_prefix = "__PYGPT_ANNOTATION_ADD__:"

        if text.startswith(remove_prefix):
            try:
                annotation_id = int(text[len(remove_prefix):].strip())
            except Exception:
                return True
            QTimer.singleShot(0, lambda aid=annotation_id: self._remove_annotation(aid))
            return True

        if text.startswith(add_prefix):
            try:
                payload = json.loads(text[len(add_prefix):])
            except Exception:
                return True
            if not isinstance(payload, dict):
                return True
            data = {
                "selection": str(payload.get("selection") or ""),
                "element": payload.get("element") if isinstance(payload.get("element"), dict) else {},
                "note": str(payload.get("note") or ""),
            }
            QTimer.singleShot(0, lambda item=data: self.add_annotation(
                selection=item["selection"], element=item["element"], note=item["note"]
            ))
            return True

        return False

    def _remove_annotation(self, annotation_id: int):
        annotation_id = int(annotation_id)
        before = len(self.annotations)
        self.annotations = [x for x in self.annotations if int(x.get("id", -1)) != annotation_id]
        if len(self.annotations) == before:
            return False
        self._render_annotations()
        try:
            self.window.update_status(
                f"{trans('ui.annotation_removed', domain='plugin.canvas_web')} #{annotation_id}"
            )
        except Exception:
            pass
        return True

    def _annotation_overlay_script(self):
        payload = []
        current = str(self.current_url() or "")
        for item in self.annotations:
            # An annotation belongs to the page on which it was created. Runtime
            # documents may keep the same logical page under about:blank/base URL,
            # so only suppress a clearly different non-empty URL.
            item_url = str(item.get("url") or "")
            if item_url and current and item_url != current and item_url != "about:blank" and current != "about:blank":
                continue
            payload.append({
                "id": int(item.get("id", 0)),
                "note": str(item.get("note") or ""),
                "selection": str(item.get("selection") or ""),
                "element": item.get("element") if isinstance(item.get("element"), dict) else {},
            })
        data = json.dumps(payload, ensure_ascii=False)
        backend = json.dumps(self.backend)
        return r"""(() => {
          const items = __DATA__;
          const backend = __BACKEND__;
          try { if (typeof window.__pygptAnnotationCleanup === 'function') window.__pygptAnnotationCleanup(); } catch (_) {}
          window.__pygptAnnotationCleanup = null;
          let root = document.getElementById('__pygpt_annotations_root');
          if (root) root.remove();
          if (!items.length) return 0;

          root = document.createElement('div');
          root.id = '__pygpt_annotations_root';
          root.setAttribute('data-pygpt-ui', 'annotations');
          Object.assign(root.style, {position:'fixed', inset:'0', zIndex:'2147483645', pointerEvents:'none', fontFamily:'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'});
          document.documentElement.appendChild(root);

          const esc = (v) => String(v == null ? '' : v);
          const place = (box, card, mark, item) => {
            const e = item.element || {};
            let target = null;
            try { if (e.selector) target = document.querySelector(e.selector); } catch (_) {}
            let r = target ? target.getBoundingClientRect() : null;
            if (!r || (!r.width && !r.height)) {
              r = {x:Number(e.x||12), y:Number(e.y||12), width:Math.max(8,Number(e.width||24)), height:Math.max(8,Number(e.height||24)), left:Number(e.x||12), top:Number(e.y||12), right:Number(e.x||12)+Math.max(8,Number(e.width||24)), bottom:Number(e.y||12)+Math.max(8,Number(e.height||24))};
            }
            let hr = r;
            const sr = e.selectionRect;
            if (sr && target) {
              hr = {left:r.left+Number(sr.dx||0), top:r.top+Number(sr.dy||0), width:Math.max(3,Number(sr.width||3)), height:Math.max(3,Number(sr.height||3))};
              hr.right = hr.left + hr.width; hr.bottom = hr.top + hr.height;
            }
            Object.assign(box.style, {left:Math.round(hr.left-3)+'px', top:Math.round(hr.top-3)+'px', width:Math.round(Math.max(6,hr.width)+6)+'px', height:Math.round(Math.max(6,hr.height)+6)+'px'});
            const cardW = Math.min(330, Math.max(220, window.innerWidth - 24));
            let left = Math.min(window.innerWidth-cardW-10, Math.max(10, hr.left));
            let top = hr.bottom + 10;
            const estimated = Math.max(68, card.offsetHeight || 82);
            if (top + estimated > window.innerHeight - 10) top = Math.max(10, hr.top - estimated - 10);
            const offset = ((Number(item.id)||1)-1) % 4 * 7;
            left = Math.min(window.innerWidth-cardW-10, left + offset);
            top = Math.min(window.innerHeight-estimated-10, Math.max(10, top + offset));
            card.style.left = Math.round(left)+'px'; card.style.top = Math.round(top)+'px'; card.style.width = Math.round(cardW)+'px';
            mark.style.left = Math.round(Math.max(2, hr.left-10))+'px'; mark.style.top = Math.round(Math.max(2, hr.top-10))+'px';
          };

          for (const item of items) {
            const box = document.createElement('div');
            box.className = '__pygpt_annotation_box';
            Object.assign(box.style, {position:'fixed', border:'2px solid #a855f7', background:'rgba(168,85,247,.10)', borderRadius:'5px', boxSizing:'border-box', boxShadow:'0 0 0 2px rgba(168,85,247,.12)', pointerEvents:'none'});

            const mark = document.createElement('div');
            mark.textContent = String(item.id);
            Object.assign(mark.style, {position:'fixed', minWidth:'22px', height:'22px', padding:'0 5px', display:'flex', alignItems:'center', justifyContent:'center', background:'#7c3aed', color:'#fff', borderRadius:'11px', fontSize:'11px', fontWeight:'700', boxSizing:'border-box', boxShadow:'0 2px 8px rgba(0,0,0,.28)', pointerEvents:'none'});

            const card = document.createElement('div');
            card.className = '__pygpt_annotation_card';
            Object.assign(card.style, {position:'fixed', boxSizing:'border-box', padding:'10px 34px 10px 11px', background:'rgba(26,27,31,.96)', color:'#f7f7f8', border:'1px solid rgba(168,85,247,.85)', borderRadius:'9px', boxShadow:'0 8px 28px rgba(0,0,0,.32)', fontSize:'12px', lineHeight:'1.38', whiteSpace:'pre-wrap', overflowWrap:'anywhere', maxHeight:'min(280px,40vh)', overflowY:'auto', pointerEvents:'auto'});
            const title = document.createElement('div');
            title.textContent = __ANNOTATION_TITLE__ + ' #' + item.id;
            Object.assign(title.style, {fontWeight:'700', color:'#d8b4fe', marginBottom:'4px'});
            const body = document.createElement('div');
            body.textContent = esc(item.note || item.selection || __ANNOTATION_TITLE__);
            const close = document.createElement('button');
            close.type = 'button'; close.textContent = '×'; close.title = __REMOVE_ANNOTATION__;
            Object.assign(close.style, {position:'absolute', right:'6px', top:'5px', width:'24px', height:'24px', border:'0', borderRadius:'5px', background:'transparent', color:'#ddd', fontSize:'20px', lineHeight:'20px', cursor:'pointer', padding:'0'});
            close.onmouseenter = () => close.style.background='rgba(255,255,255,.10)';
            close.onmouseleave = () => close.style.background='transparent';
            close.onclick = (ev) => {
              ev.preventDefault(); ev.stopPropagation();
              box.remove(); mark.remove(); card.remove();
              try {
                if (backend === 'playwright' && typeof window.__pygpt_remove_annotation === 'function') {
                  window.__pygpt_remove_annotation(item.id);
                } else {
                  console.info('__PYGPT_ANNOTATION_REMOVE__:' + item.id);
                }
              } catch (_) {}
            };
            card.append(title, body, close);
            root.append(box, mark, card);
            const update = () => { if (box.isConnected) place(box, card, mark, item); };
            update();
            root.__pygptUpdates = root.__pygptUpdates || []; root.__pygptUpdates.push(update);
          }
          let raf = 0;
          const updateAll = () => { raf = 0; if (!root.isConnected) return; for (const fn of (root.__pygptUpdates||[])) fn(); };
          const schedule = () => { if (!raf) raf = requestAnimationFrame(updateAll); };
          window.addEventListener('scroll', schedule, true);
          window.addEventListener('resize', schedule, true);
          window.__pygptAnnotationCleanup = () => {
            window.removeEventListener('scroll', schedule, true);
            window.removeEventListener('resize', schedule, true);
            if (raf) cancelAnimationFrame(raf);
          };
          return items.length;
        })()""".replace('__DATA__', data) \
            .replace('__BACKEND__', backend) \
            .replace('__ANNOTATION_TITLE__', json.dumps(trans('ui.annotation_title', domain='plugin.canvas_web'), ensure_ascii=False)) \
            .replace('__REMOVE_ANNOTATION__', json.dumps(trans('ui.remove_annotation', domain='plugin.canvas_web'), ensure_ascii=False))

    def _render_annotations(self):
        if self.surface is None:
            return
        script = self._annotation_overlay_script()
        try:
            if self.backend == "playwright":
                if self.pw_page is None:
                    return
                self.pw_page.evaluate(script)
                self._schedule_playwright_frame(10)
            else:
                # Async avoids nesting an event loop when called from a WebEngine
                # navigation callback or context-menu action.
                self.surface.web.page().runJavaScript(script)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass

    def get_annotations(self):
        return list(self.annotations)
