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
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from ..ui.widgets import BrowserViewport


class CanvasViewport:
    """Manage Qt surface attachment, sizing and pointer coordinates."""

    def __init__(self, runtime):
        self.runtime = runtime

    def on_user_interaction(self):
        """Select the clicked session even when Qt keyboard focus has not changed."""
        runtime = self.runtime
        root = runtime.runtime_root or runtime
        root.mark_surface_used(runtime)
        owner = runtime.surface_owner
        tab = getattr(owner, "tab", None)
        if tab is not None:
            runtime.window.controller.tabs.on_column_focus(tab.column_idx)

    def ensure_surface(self):
        runtime = self.runtime
        if runtime.surface is not None:
            return runtime.surface
        runtime.width = int(runtime._opt("default_width", 1280) or 1280)
        runtime.height = int(runtime._opt("default_height", 800) or 800)
        runtime.orientation = "landscape" if runtime.width >= runtime.height else "portrait"
        runtime.hidden_host = QWidget(runtime.window)
        runtime.hidden_layout = QVBoxLayout(runtime.hidden_host)
        runtime.hidden_layout.setContentsMargins(0, 0, 0, 0)
        runtime.surface = BrowserViewport(runtime.window, runtime)
        runtime.surface.set_resolution(runtime.width, runtime.height)
        runtime.hidden_layout.addWidget(runtime.surface)
        runtime.pw_frame_timer = QTimer(runtime)
        runtime.pw_frame_timer.setInterval(250)
        runtime.pw_frame_timer.timeout.connect(runtime.playwright.poll_frame)
        runtime.hidden_host.hide()
        try:
            runtime.surface.web.urlChanged.connect(runtime.history.on_qt_url_changed)
            runtime.surface.web.titleChanged.connect(runtime.history.on_qt_title_changed)
        except Exception:
            pass
        # The start page is loaded only when the Canvas runtime is actually
        # created, preserving the existing lazy WebEngine/Playwright startup.
        runtime.load_start_page()
        return runtime.surface

    def attach_surface(self, owner):
        runtime = self.runtime
        surface = self.ensure_surface()
        if runtime.surface_owner is owner:
            owner.attach_runtime_surface(surface)
            return
        if runtime.surface_owner is not None:
            try:
                runtime.surface_owner._take_surface()
            except Exception:
                pass
        else:
            try:
                runtime.hidden_layout.removeWidget(surface)
            except Exception:
                pass
        surface.setParent(None)
        runtime.surface_owner = owner
        owner.attach_runtime_surface(surface)
        if getattr(owner, "tab", None) is not None:
            surface.set_tab(owner.tab)
        runtime.notify_state()
        try:
            owner.request_viewport_sync(immediate=True)
        except Exception:
            pass

    def detach_surface(self, owner=None):
        runtime = self.runtime
        if runtime.surface is None:
            return
        if owner is not None and runtime.surface_owner is not owner:
            return
        if runtime.surface_owner is not None:
            try:
                runtime.surface_owner._take_surface()
            except Exception:
                pass
        runtime.surface_owner = None
        if runtime.hidden_layout is not None:
            runtime.surface.setParent(runtime.hidden_host)
            runtime.hidden_layout.addWidget(runtime.surface)
        self.request_viewport_policy(visible=False, delay=0)
        runtime.notify_state()

    def app_busy(self) -> bool:
        """Return True while the application/model request is actively running."""
        runtime = self.runtime
        try:
            kernel = getattr(runtime.window.controller, "kernel", None)
            if kernel is not None:
                return bool(getattr(kernel, "busy", False))
        except Exception:
            pass
        try:
            return getattr(runtime.window, "state", None) == getattr(runtime.window, "STATE_BUSY", "busy")
        except Exception:
            return False

    def request_viewport_policy(self, width=None, height=None, visible=True, delay: int = 0):
        """Queue Canvas viewport synchronization with the current UI geometry.

        Visible Canvas uses the real available column area. A fully hidden
        Canvas uses the last model-requested resolution, or plugin defaults when
        the model has not selected a resolution yet. While the app is BUSY the
        request is retained and applied only after it returns to IDLE.
        """
        runtime = self.runtime
        runtime.ui_viewport_visible = bool(visible)
        if visible and width is not None and height is not None:
            width = int(width)
            height = int(height)
            if width > 0 and height > 0:
                runtime.ui_viewport_target = (width, height)
        if runtime.viewport_policy_timer is None:
            return
        runtime.viewport_policy_timer.start(max(0, int(delay)))

    def hidden_resolution(self):
        """Return the runtime size used while the Canvas column is fully hidden."""
        runtime = self.runtime
        if runtime.model_resolution is not None:
            return runtime.model_resolution
        width = int(runtime._opt("default_width", 1280) or 1280)
        height = int(runtime._opt("default_height", 800) or 800)
        return max(240, min(width, 7680)), max(180, min(height, 4320))

    def apply_viewport_policy(self):
        """Apply a queued UI/background viewport transition when it is safe."""
        runtime = self.runtime
        if runtime.surface is None:
            return
        if self.app_busy():
            # Do not compete with canvas_change_resolution while the model is
            # using the runtime. Keep retrying until the application is IDLE.
            runtime.viewport_policy_timer.start(120)
            return

        if runtime.ui_viewport_visible and runtime.ui_viewport_target is not None:
            width, height = runtime.ui_viewport_target
            changed = self.set_resolution(width, height, "auto", clamp_min=False)
        else:
            width, height = self.hidden_resolution()
            changed = self.set_resolution(width, height, "auto", clamp_min=True)

        if changed:
            runtime.notify_state()

    def set_resolution(self, width, height, orientation="auto", clamp_min: bool = True):
        runtime = self.runtime
        min_width = 240 if clamp_min else 1
        min_height = 180 if clamp_min else 1
        width = max(min_width, min(int(width), 7680))
        height = max(min_height, min(int(height), 4320))
        orientation = str(orientation or "auto").lower()
        if orientation == "portrait" and width > height:
            width, height = height, width
        elif orientation == "landscape" and height > width:
            width, height = height, width
        if width == runtime.width and height == runtime.height:
            return False
        runtime.width, runtime.height = width, height
        runtime.orientation = "landscape" if width >= height else "portrait"
        runtime.surface.set_resolution(width, height)
        if runtime.pw_page is not None:
            runtime.pw_page.set_viewport_size({"width": width, "height": height})
            runtime.playwright.refresh_frame()
        runtime.cursor_x = min(runtime.cursor_x, width - 1)
        runtime.cursor_y = min(runtime.cursor_y, height - 1)
        runtime.qt.update_cursor()
        return True

    @staticmethod
    def parse_resolution(value):
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return int(value[0]), int(value[1])
        text = str(value).lower().replace(" ", "")
        if "x" in text:
            a, b = text.split("x", 1)
            return int(a), int(b)
        raise ValueError("resolution must be WIDTHxHEIGHT or [width,height]")

    def clamp(self, x, y):
        runtime = self.runtime
        return max(0, min(runtime.width - 1, int(x))), max(0, min(runtime.height - 1, int(y)))

    def point(self, p):
        runtime = self.runtime
        if p.get("x") is None or p.get("y") is None:
            raise ValueError("x and y are required when selector is omitted")
        return self.clamp(int(p["x"]), int(p["y"]))

    def draw_cursor_on_pixmap(self, pixmap, x=None, y=None):
        runtime = self.runtime
        from PySide6.QtGui import QPainter, QPen
        if pixmap is None or pixmap.isNull() or not runtime.cursor_visible:
            return
        painter = QPainter(pixmap)
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(2)
        painter.setPen(pen)
        x = int(runtime.cursor_x if x is None else x)
        y = int(runtime.cursor_y if y is None else y)
        painter.drawEllipse(x - 7, y - 7, 14, 14)
        painter.drawLine(x - 11, y, x + 11, y)
        painter.drawLine(x, y - 11, x, y + 11)
        painter.end()

    def qt_key_to_playwright(self, event):
        runtime = self.runtime
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
