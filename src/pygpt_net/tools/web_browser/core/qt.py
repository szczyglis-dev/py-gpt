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
import json

from PySide6.QtCore import QEventLoop, QTimer


class QtBackend:
    """Evaluate scripts and synchronize state with Qt WebEngine."""

    def __init__(self, runtime):
        self.runtime = runtime

    def load_html(self, html, base_url, timeout_ms=15000, *, wait=True):
        """Wait for the new document before acknowledging a Canvas update.

        A document update can emit loadFinished(False) for the interrupted
        previous load. Only a successful completion makes the new page ready.
        """
        web = self.runtime.surface.web
        # Keep the page for ordinary document updates. Replacing it while a
        # navigation is finishing can destroy Chromium's active render widget.
        # Profile/session changes explicitly reset the page in reset_session().
        if not wait:
            web.setHtml(html, base_url)
            return
        page = web.page()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        loaded = False

        def finished(success):
            nonlocal loaded
            if success:
                loaded = True
                loop.quit()

        page.loadFinished.connect(finished)
        page.destroyed.connect(loop.quit)
        try:
            timer.start(timeout_ms)
            web.setHtml(html, base_url)
            if not loaded:
                loop.exec()
            if not loaded:
                raise TimeoutError("Canvas HTML document did not finish loading")
        finally:
            timer.stop()
            try:
                page.loadFinished.disconnect(finished)
                page.destroyed.disconnect(loop.quit)
            except RuntimeError:
                # Closing a tab while waiting may already have deleted its page.
                pass

    def js(self, script: str, timeout_ms: int = 10000):
        runtime = self.runtime
        loop = QEventLoop()
        box = {"done": False, "value": None}

        def callback(value):
            box["done"] = True
            box["value"] = value
            if loop.isRunning():
                loop.quit()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        try:
            timer.start(timeout_ms)
            runtime.surface.web.page().runJavaScript(script, 0, callback)
            if not box["done"]:
                loop.exec()
        finally:
            timer.stop()
        if not box["done"]:
            raise TimeoutError("WebEngine JavaScript operation timed out")
        return box["value"]

    def html(self):
        runtime = self.runtime
        loop = QEventLoop()
        box = {"done": False, "value": ""}

        def callback(value):
            box["done"] = True
            box["value"] = value or ""
            if loop.isRunning():
                loop.quit()

        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        try:
            timer.start(10000)
            runtime.surface.web.page().toHtml(callback)
            if not box["done"]:
                loop.exec()
        finally:
            timer.stop()
        if not box["done"]:
            raise TimeoutError("WebEngine HTML serialization timed out")
        return box["value"]

    def delay(self, seconds):
        runtime = self.runtime
        loop = QEventLoop()
        QTimer.singleShot(max(0, int(float(seconds) * 1000)), loop.quit)
        loop.exec()

    def on_load_finished(self, success: bool):
        runtime = self.runtime
        # An aborted old navigation, or a hidden Qt page while Playwright is
        # active, must not rewrite history or attach overlays to the new page.
        if (getattr(runtime, "_closing", False) or runtime.surface is None
                or not success or runtime.backend != "qt"):
            return
        runtime.virtual_url = runtime.surface.web.url().toString() or runtime.virtual_url
        if runtime._history_loading:
            runtime.history.update_current_url(runtime.virtual_url)
            runtime._history_loading = False
        elif not runtime.blank_canvas_active:
            runtime.history.record_navigation(runtime.virtual_url)
        if success and runtime.current_canvas_history_is_url():
            try:
                title = runtime.surface.web.title()
            except Exception:
                title = ""
            runtime.history.record(runtime.virtual_url, title)
        self.update_cursor()
        runtime._render_annotations()
        runtime.notify_state()
        if runtime._source_reload_pending:
            runtime._source_reload_pending = False
            # Source was visible when a real URL/file was reloaded. Replace the
            # edited buffer with the freshly loaded document instead of letting
            # those discarded edits linger in the editor.
            QTimer.singleShot(0, runtime.document.show_source)

    def update_cursor(self):
        runtime = self.runtime
        if runtime.backend != "qt":
            return
        if not runtime.cursor_visible:
            script = """(() => { const c=document.getElementById('__pygpt_virtual_cursor'); if(c)c.remove(); return true; })()"""
        else:
            x, y = runtime.cursor_x, runtime.cursor_y
            script = f"""(() => {{
let c=document.getElementById('__pygpt_virtual_cursor');
if(!c){{c=document.createElement('div');c.id='__pygpt_virtual_cursor';Object.assign(c.style,{{position:'fixed',zIndex:'2147483647',width:'14px',height:'14px',border:'2px solid #ff2d55',borderRadius:'50%',pointerEvents:'none',boxSizing:'border-box'}});document.documentElement.appendChild(c);}}
c.style.left='{x-7}px'; c.style.top='{y-7}px'; return true; }})()"""
        try:
            runtime.surface.web.page().runJavaScript(script)
        except Exception:
            pass

    def eval(self, script):
        runtime = self.runtime
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            try:
                result = runtime.pw_page.evaluate(script)
            except Exception as first_exc:
                # Playwright evaluate accepts expressions/functions. As a convenience,
                # also accept a plain JavaScript function body like Qt runJavaScript does.
                try:
                    result = runtime.pw_page.evaluate(f"() => {{ {script} }}")
                except Exception:
                    raise first_exc
            runtime.playwright.refresh_frame()
            return result
        # Tool-side inspection snippets often declare names such as `canvas`
        # which the page already uses. Give each evaluation a local scope while
        # retaining normal script completion values and access to page globals.
        return self.js(f"(() => {{ return eval({json.dumps(script)}); }})()")
