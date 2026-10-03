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
import os
from PySide6.QtCore import QTimer


class PlaywrightBackend:
    """Manage Playwright lifecycle, navigation and frame delivery."""

    def __init__(self, runtime):
        self.runtime = runtime

    def ensure(self):
        runtime = self.runtime
        if runtime.pw_page is not None:
            try:
                _ = runtime.pw_page.url
                return
            except Exception:
                self.stop()
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError("Playwright is required for sandbox=true. Install it and a browser, e.g. `pip install playwright && playwright install chromium`.") from exc
        path = str(runtime._opt("playwright_path", "") or "").strip()
        engine = str(runtime._opt("playwright_engine", "chromium") or "chromium")
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
        args = [x.strip() for x in str(runtime._opt("playwright_args", "") or "").split(",") if x.strip()]
        try:
            root = runtime.runtime_root or runtime
            if root._playwright_driver is None:
                root._playwright_driver = sync_playwright().start()
            runtime.pw = root._playwright_driver
            root._playwright_users.add(runtime)
            launcher = getattr(runtime.pw, engine)
            kwargs = {"headless": True}
            if args and engine == "chromium":
                kwargs["args"] = args
            runtime.pw_browser = launcher.launch(**kwargs)
            runtime.pw_context = runtime.pw_browser.new_context(viewport={"width": runtime.width, "height": runtime.height})
            runtime.pw_page = runtime.pw_context.new_page()
            runtime.pw_page.expose_binding("__pygpt_remove_annotation", runtime.annotation_bridge.remove_binding)
            runtime.pw_page.expose_binding("__pygpt_add_annotation", runtime.annotation_bridge.add_binding)
            runtime.pw_page.on("console", lambda msg: runtime.append_console("console", getattr(msg, "type", "log"), getattr(msg, "text", "")))
            runtime.pw_page.on("pageerror", lambda exc: runtime.append_console("pageerror", "error", str(exc)))
            runtime.pw_page.goto("about:blank")
            runtime.pw_page.set_content(runtime.blank_canvas_html(), wait_until="domcontentloaded")
            runtime.blank_canvas_active = True
            runtime.virtual_url = "about:blank"
            runtime.pw_page.on("framenavigated", self.on_navigated)
            runtime.pw_page.on("load", lambda: self.on_loaded())
            if runtime.pw_frame_timer is not None and not runtime.pw_frame_timer.isActive():
                runtime.pw_frame_timer.start()
            self.refresh_frame()
        except Exception:
            self.stop()
            raise

    def stop(self):
        runtime = self.runtime
        if runtime.pw_frame_timer is not None:
            runtime.pw_frame_timer.stop()
        for obj, method in ((runtime.pw_page, "close"), (runtime.pw_context, "close"), (runtime.pw_browser, "close")):
            if obj is not None:
                try:
                    getattr(obj, method)()
                except Exception:
                    pass
        root = runtime.runtime_root or runtime
        root._playwright_users.discard(runtime)
        if not root._playwright_users and root._playwright_driver is not None:
            try:
                root._playwright_driver.stop()
            except Exception:
                pass
            finally:
                root._playwright_driver = None
        runtime.pw_page = None
        runtime.pw_context = None
        runtime.pw_browser = None
        runtime.pw = None
        runtime.pw_history = []
        runtime.pw_history_index = -1
        runtime.pw_history_mode = None

    def on_loaded(self):
        """Persist the final document title after a Playwright page load."""
        runtime = self.runtime
        if runtime.pw_page is None or not runtime.current_canvas_history_is_url():
            return
        try:
            runtime.history.update_title(runtime.pw_page.url, runtime.pw_page.title())
        except Exception:
            pass
        runtime.notify_state()

    def on_navigated(self, frame):
        runtime = self.runtime
        if runtime.pw_page is None:
            return
        try:
            if frame != runtime.pw_page.main_frame:
                return
            url = str(frame.url or "")
        except Exception:
            return
        if not url:
            return
        if runtime._history_loading:
            runtime.history.update_current_url(url)
        else:
            runtime.history.record_navigation(url)
        if runtime.current_canvas_history_is_url():
            try:
                title = runtime.pw_page.title() if runtime.pw_page is not None else ""
            except Exception:
                title = ""
            runtime.history.record(url, title)
        mode = runtime.pw_history_mode
        if mode == "back":
            if runtime.pw_history_index > 0:
                runtime.pw_history_index -= 1
            if 0 <= runtime.pw_history_index < len(runtime.pw_history):
                runtime.pw_history[runtime.pw_history_index] = url
            runtime.pw_history_mode = None
        elif mode == "forward":
            if runtime.pw_history_index + 1 < len(runtime.pw_history):
                runtime.pw_history_index += 1
            if 0 <= runtime.pw_history_index < len(runtime.pw_history):
                runtime.pw_history[runtime.pw_history_index] = url
            runtime.pw_history_mode = None
        elif mode == "reload":
            if 0 <= runtime.pw_history_index < len(runtime.pw_history):
                runtime.pw_history[runtime.pw_history_index] = url
        else:
            current = runtime.pw_history[runtime.pw_history_index] if 0 <= runtime.pw_history_index < len(runtime.pw_history) else None
            if current != url:
                runtime.pw_history = runtime.pw_history[:runtime.pw_history_index + 1]
                runtime.pw_history.append(url)
                if len(runtime.pw_history) > runtime.HISTORY_LIMIT:
                    overflow = len(runtime.pw_history) - runtime.HISTORY_LIMIT
                    runtime.pw_history = runtime.pw_history[overflow:]
                runtime.pw_history_index = len(runtime.pw_history) - 1
        if url != "about:blank":
            runtime.virtual_url = url
        # Avoid nested Playwright sync calls (e.g. title/evaluate) from inside a
        # Playwright event callback. Restore overlays and publish state on the
        # next Qt turn instead.
        QTimer.singleShot(0, self.restore_annotations)
        QTimer.singleShot(0, runtime.notify_state)

    def restore_annotations(self):
        runtime = self.runtime
        try:
            runtime._render_annotations()
            if runtime.backend == "playwright" and runtime.pw_page is not None:
                self.schedule_frame(10)
        except Exception as exc:
            try:
                runtime.window.core.debug.log(exc)
            except Exception:
                pass

    def refresh_frame(self):
        runtime = self.runtime
        runtime.pw_frame_pending = False
        if runtime.pw_page is None:
            return
        data = runtime.pw_page.screenshot(type="png")
        runtime.surface.sandbox.set_frame(data)
        page_url = runtime.pw_page.url
        if page_url and page_url != "about:blank":
            runtime.virtual_url = page_url
        runtime.surface.sandbox.update()
        runtime.notify_state()

    def poll_frame(self):
        """Refresh the remote framebuffer while it is actually visible to the user."""
        runtime = self.runtime
        if runtime.backend != "playwright" or runtime.pw_page is None or runtime.surface_owner is None:
            return
        if runtime.surface is not None and runtime.surface._source_visible:
            return
        scroll = getattr(runtime.surface_owner, "scroll", None)
        if scroll is not None and not scroll.isVisible():
            return
        try:
            data = runtime.pw_page.screenshot(type="png")
            runtime.surface.sandbox.set_frame(data)
            page_url = runtime.pw_page.url
            if page_url and page_url != "about:blank":
                runtime.virtual_url = page_url
        except Exception as exc:
            try:
                runtime.window.core.debug.log(exc)
            except Exception:
                pass

    def schedule_frame(self, delay_ms: int = 70):
        runtime = self.runtime
        if runtime.pw_frame_pending or runtime.pw_page is None:
            return
        runtime.pw_frame_pending = True
        QTimer.singleShot(max(0, int(delay_ms)), self.refresh_frame)

    def user_action(self, op: str, p: dict):
        runtime = self.runtime
        if runtime.backend != "playwright":
            return
        try:
            self.ensure()
            if op == "hover":
                x, y = runtime.viewport.clamp(int(p["x"]), int(p["y"]))
                runtime.pw_page.mouse.move(x, y)
            elif op == "mouse_down":
                x, y = runtime.viewport.clamp(int(p["x"]), int(p["y"]))
                runtime.pw_page.mouse.move(x, y)
                runtime.pw_page.mouse.down(button=p.get("button", "left"))
            elif op == "mouse_up":
                x, y = runtime.viewport.clamp(int(p["x"]), int(p["y"]))
                runtime.pw_page.mouse.move(x, y)
                runtime.pw_page.mouse.up(button=p.get("button", "left"))
            elif op == "click":
                runtime.pw_page.mouse.click(int(p["x"]), int(p["y"]), click_count=int(p.get("count", 1)))
            elif op == "scroll":
                runtime.pw_page.mouse.wheel(int(p.get("dx", 0)), int(p.get("dy", 0)))
            elif op == "type_raw":
                runtime.pw_page.keyboard.type(str(p.get("text", "")))
            elif op == "key":
                runtime.pw_page.keyboard.press(str(p.get("key") or ""))
            if op == "hover":
                self.schedule_frame()
            else:
                self.refresh_frame()
        except Exception as exc:
            runtime.window.core.debug.log(exc)
