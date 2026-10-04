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
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin
from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap


from .preview import _PreviewHandler


class CanvasCommands:
    """Execute Canvas commands against an individual runtime."""

    def __init__(self, runtime):
        self.runtime = runtime

    def execute(self, cmd: str, params: dict, plugin=None):
        runtime = self.runtime
        # Keep old internal calls/conversation tool calls functional after the
        # public API rename; only canvas_* names are exposed to the model.
        if isinstance(cmd, str) and cmd.startswith("web_browser_"):
            cmd = "canvas_" + cmd[len("web_browser_"):]
        params = dict(params or {})
        params.setdefault("__agent", plugin is not None and not params.get("__ui"))
        runtime.viewport.ensure_surface()
        # Playwright is opt-in. If the user disables the master switch while a
        # sandbox session exists, the next operation cleanly returns to QWebEngine.
        if not runtime.sandbox_enabled() and runtime.backend == "playwright":
            runtime.set_backend("qt")
        handlers = {
            "canvas_open": self.open,
            "canvas_change_resolution": self.resolution,
            "canvas_set_html": self.set_html,
            "canvas_get_html": self.get_html,
            "canvas_current": lambda p: runtime.current_state(),
            "canvas_close": lambda p: runtime.close_surface(),
            "canvas_prev": self.prev,
            "canvas_next": self.next,
            "canvas_reload": self.reload,
            "canvas_screenshot": self.screenshot,
            "canvas_inspect": self.inspect,
            "canvas_click": self.click,
            "canvas_hover": self.hover,
            "canvas_type": self.type,
            "canvas_key": self.key,
            "canvas_scroll": self.scroll,
            "canvas_drag": self.drag,
            "canvas_wait": self.wait,
            "canvas_eval": self.eval,
            "canvas_select": self.select,
            "canvas_check": self.check,
            "canvas_upload": self.upload,
            "canvas_console": self.console,
            "canvas_annotations": self.annotations,
            "canvas_clear_annotations": lambda p: self.clear_annotations(),
            "web_server_start": self.server_start,
            "web_server_current": lambda p: runtime.preview.state(),
            "web_server_stop": lambda p: self.server_stop(),
        }
        handler = handlers.get(cmd)
        if handler is None:
            raise ValueError(f"Unsupported Canvas/Web Browser command: {cmd}")
        result = handler(params)
        runtime.notify_state()
        return result

    def open(self, p):
        runtime = self.runtime
        runtime.document.revision += 1
        if not p.get("__startup") and runtime.auto_open_enabled():
            runtime.ensure_visible_surface()
        sandbox_arg = p.get("sandbox")
        sandbox_enabled = runtime.sandbox_enabled()
        if not sandbox_enabled:
            # Master switch OFF: never import/start Playwright, regardless of what
            # the model requested. This keeps the built-in QWebEngine path silent.
            sandbox = False
            lock_agent_backend = False
        else:
            sandbox = sandbox_arg
            if sandbox is None:
                sandbox = runtime.backend == "playwright" if p.get("__ui") else True
            lock_agent_backend = bool(p.get("__agent") and sandbox_arg is not None)
        resolution = p.get("resolution")
        if resolution:
            width, height = runtime.viewport.parse_resolution(resolution)
            runtime.viewport.set_resolution(width, height, "auto")
            if p.get("__agent"):
                runtime.model_resolution = (runtime.width, runtime.height)
                # The model owns the viewport for the duration of BUSY. Once it
                # becomes IDLE, re-apply the visible UI fit (or hidden fallback).
                runtime.viewport_policy_timer.start(120)
        mode = "playwright" if bool(sandbox) else "qt"
        runtime.set_backend(mode)
        if p.get("__agent"):
            runtime.agent_backend_locked = lock_agent_backend
        url = runtime.document.resolve_url(str(p.get("url") or ""), p.get("__workdir"))
        if not url:
            url = runtime.virtual_url or "about:blank"
        if not p.get("__history_restore"):
            runtime.history.push({"kind": "url", "url": url})
        runtime._history_loading = True
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.pw_page.goto(url, wait_until="domcontentloaded")
            if url == "about:blank":
                runtime.render_blank_canvas()
            else:
                runtime.blank_canvas_active = False
                runtime.virtual_url = runtime.pw_page.url
                runtime.playwright.refresh_frame()
        else:
            if url == "about:blank":
                runtime.render_blank_canvas()
            else:
                runtime.blank_canvas_active = False
                runtime.surface.web.setUrl(QUrl.fromUserInput(url))
                runtime.virtual_url = url
        if runtime.backend == "playwright":
            runtime._history_loading = False
        return runtime.current_state()

    def resolution(self, p):
        runtime = self.runtime
        width = int(p.get("width") or runtime.width)
        height = int(p.get("height") or runtime.height)
        orientation = str(p.get("orientation") or "auto").lower()
        runtime.viewport.set_resolution(width, height, orientation)
        if p.get("__agent"):
            runtime.model_resolution = (runtime.width, runtime.height)
            runtime.viewport_policy_timer.start(120)
        return runtime.current_state()

    def set_html(self, p):
        runtime = self.runtime
        runtime.document.revision += 1
        runtime._source_reload_pending = False
        if runtime.auto_open_enabled():
            runtime.ensure_visible_surface()
        if (runtime.sandbox_enabled() and p.get("__agent")
                and not runtime.agent_backend_locked and runtime.backend != "playwright"):
            runtime.set_backend("playwright")
        html = str(p.get("html") or "")
        workdir = p.get("__workdir") or os.getcwd()
        base_url = runtime.document.normalize_base_url(p.get("base_url"), workdir)
        runtime_base = base_url
        runtime.base_url = base_url
        if not p.get("__history_restore"):
            entry = {
                "kind": "html",
                "html": html,
                "base_url": base_url,
                "workdir": workdir,
            }
            # Keep the fetched page's origin across repeated source edits.
            if p.get("__source_edit") and 0 <= runtime.canvas_history_index < len(runtime.canvas_history):
                previous = runtime.canvas_history[runtime.canvas_history_index]
                reload_url = (previous.get("url") if previous.get("kind") == "url"
                              else previous.get("reload_url"))
                if reload_url and QUrl(reload_url).scheme().lower() in ("http", "https", "file"):
                    entry["reload_url"] = reload_url
            runtime.history.push(entry)
        runtime._history_loading = True
        if getattr(runtime.surface, "_source_visible", False):
            # A model update supersedes the editor buffer as well as the page.
            # Returning from Source must not recommit an older edited document.
            runtime.surface.show_source(html, base_url=base_url)
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.blank_canvas_active = False
            qbase = QUrl(base_url) if base_url else QUrl()
            if qbase.isLocalFile():
                server_root = qbase.toLocalFile()
                if os.path.isfile(server_root):
                    server_root = os.path.dirname(server_root)
                runtime.preview.start(server_root, 0)
                runtime_base = runtime.server_url
            else:
                # Even with a remote <base>, serve the runtime document itself from
                # loopback so reload/history have a real URL and not about:blank.
                runtime.preview.start(workdir, 0)
            runtime.base_url = runtime_base
            runtime.runtime_html = runtime.document.inject_base(html, runtime_base)
            runtime_url = urljoin(runtime.server_url, _PreviewHandler.RUNTIME_PATH.lstrip("/"))
            runtime.pw_page.goto(runtime_url, wait_until="domcontentloaded")
            runtime.virtual_url = runtime.pw_page.url
            runtime.playwright.refresh_frame()
        else:
            runtime.blank_canvas_active = False
            runtime.runtime_html = html
            runtime.qt.load_html(
                html,
                QUrl(runtime_base) if runtime_base else QUrl.fromLocalFile(str(Path(workdir).resolve()) + os.sep),
                wait=not p.get("__ui", False),
            )
            runtime.virtual_url = runtime_base or "about:blank"
        if runtime.backend == "playwright":
            runtime._history_loading = False
        return {"url": runtime.current_url(), "base_url": runtime.base_url, "backend": runtime.backend, "ok": True}

    def get_html(self, p):
        runtime = self.runtime
        html = runtime.qt.eval(runtime.JS_SERIALIZE_HTML)
        return {"url": runtime.current_url(), "html": html or ""}

    def prev(self, p):
        runtime = self.runtime
        if runtime.canvas_history:
            if runtime.canvas_history_index > 0:
                return runtime.history.restore(runtime.canvas_history_index - 1)
            return runtime.current_state()
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            if runtime.pw_history_index > 0:
                runtime.pw_history_mode = "back"
                before = runtime.pw_page.url
                runtime.pw_page.go_back(wait_until="domcontentloaded")
                if runtime.pw_history_mode == "back" or runtime.pw_page.url == before:
                    runtime.pw_history_mode = None
                runtime.playwright.refresh_frame()
        else:
            hist = runtime.surface.web.history()
            if hist.canGoBack():
                runtime._history_loading = True
                runtime.surface.web.back()
        return runtime.current_state()

    def next(self, p):
        runtime = self.runtime
        if runtime.canvas_history:
            if runtime.canvas_history_index + 1 < len(runtime.canvas_history):
                return runtime.history.restore(runtime.canvas_history_index + 1)
            return runtime.current_state()
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            if runtime.pw_history_index + 1 < len(runtime.pw_history):
                runtime.pw_history_mode = "forward"
                before = runtime.pw_page.url
                runtime.pw_page.go_forward(wait_until="domcontentloaded")
                if runtime.pw_history_mode == "forward" or runtime.pw_page.url == before:
                    runtime.pw_history_mode = None
                runtime.playwright.refresh_frame()
        else:
            hist = runtime.surface.web.history()
            if hist.canGoForward():
                runtime._history_loading = True
                runtime.surface.web.forward()
        return runtime.current_state()

    def reload(self, p):
        """Reload the current Canvas document from its committed source.

        URL-backed documents (http/https/file) are loaded again from their URL.
        Synthetic documents (set_html and similar runtime HTML) are rebuilt from
        the last committed Canvas history/runtime state. Uncommitted edits in
        Source view are deliberately discarded in both cases; Source becomes a
        committed state only after returning to the Canvas view.
        """
        runtime = self.runtime
        runtime.document.revision += 1
        entry = None
        if 0 <= runtime.canvas_history_index < len(runtime.canvas_history):
            entry = runtime.canvas_history[runtime.canvas_history_index]

        url = ""
        if isinstance(entry, dict) and entry.get("kind") == "url":
            url = str(entry.get("url") or "").strip()
        reload_url = str(entry.get("reload_url") or "") if isinstance(entry, dict) else ""
        if reload_url:
            url = reload_url
        if not url:
            url = str(runtime.current_url() or "").strip()
        scheme = QUrl(url).scheme().lower() if url else ""
        source_visible = bool(runtime.surface is not None and getattr(runtime.surface, "_source_visible", False))

        # Real URL/file reload: navigate from the external source again. Never
        # apply the editor buffer first -- F5 and the toolbar Reload button must
        # behave like a normal browser reload and discard uncommitted Source edits.
        is_html_entry = isinstance(entry, dict) and entry.get("kind") == "html"
        if (not is_html_entry or reload_url) and scheme in ("http", "https", "file"):
            if source_visible:
                runtime.surface.source.document().setModified(False)
                runtime._source_reload_pending = True
            runtime._history_loading = True
            if reload_url:
                runtime.canvas_history[runtime.canvas_history_index] = {"kind": "url", "url": url}
            if runtime.backend == "playwright":
                runtime.playwright.ensure()
                runtime.pw_history_mode = "reload"
                try:
                    if reload_url:
                        runtime.pw_page.goto(url, wait_until="domcontentloaded")
                    else:
                        runtime.pw_page.reload(wait_until="domcontentloaded")
                finally:
                    runtime.pw_history_mode = None
                    runtime._history_loading = False
                runtime.virtual_url = runtime.pw_page.url or url
                runtime.playwright.refresh_frame()
                if source_visible:
                    runtime._source_reload_pending = False
                    runtime.document.show_source()
            else:
                if reload_url:
                    runtime.surface.web.setUrl(QUrl(url))
                else:
                    runtime.surface.web.reload()
            return runtime.current_state()

        # Runtime/set_html documents are reloaded from the last committed HTML,
        # never from the currently edited Source buffer. This is intentionally
        # different from Back to canvas, which commits Source edits via
        # apply_source_html().
        if isinstance(entry, dict) and entry.get("kind") == "html":
            html = str(entry.get("html") or "")
            base_url = str(entry.get("base_url") or runtime.base_url or "")
            workdir = entry.get("workdir") or os.getcwd()
        elif runtime.blank_canvas_active:
            runtime.render_blank_canvas()
            return runtime.current_state()
        else:
            # data:/about:/other synthetic content has no external source. The
            # rendered browser document is authoritative; Source edits have not
            # touched it until Back to canvas is used.
            html = str(runtime.qt.eval(runtime.JS_SERIALIZE_HTML) or runtime.runtime_html or "")
            base_url = str(runtime.base_url or "")
            workdir = os.getcwd()

        # set_html also replaces a visible source buffer with this committed
        # document; do not serialize an older browser DOM back into the editor.
        return self.set_html({
            "html": html,
            "base_url": base_url,
            "__workdir": workdir,
            "__ui": True,
            "__history_restore": True,
        })

    def screenshot(self, p):
        runtime = self.runtime
        path = p.get("path")
        if not path:
            tmp = runtime.window.core.config.get_user_dir("tmp")
            os.makedirs(tmp, exist_ok=True)
            path = os.path.join(tmp, f"canvas_{uuid.uuid4().hex}.png")
        path = os.path.abspath(str(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            full_page = bool(p.get("full_page", False))
            runtime.pw_page.screenshot(path=path, full_page=full_page)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                cursor_y = runtime.cursor_y
                if full_page:
                    try:
                        cursor_y += int(runtime.pw_page.evaluate("window.scrollY || 0") or 0)
                    except Exception:
                        pass
                runtime.viewport.draw_cursor_on_pixmap(pixmap, runtime.cursor_x, cursor_y)
                pixmap.save(path, "PNG")
        else:
            pixmap = runtime.surface.web.grab()
            runtime.viewport.draw_cursor_on_pixmap(pixmap)
            if not pixmap.save(path, "PNG"):
                raise RuntimeError("Could not save browser screenshot")
        return {"path": path, "url": runtime.current_url(), "width": runtime.width, "height": runtime.height, "backend": runtime.backend}

    def inspect(self, p):
        runtime = self.runtime
        selector = p.get("selector")
        limit = max(1, min(int(p.get("limit") or 100), 500))
        script = runtime.JS_INSPECT % (json.dumps(selector) if selector else "null", limit)
        result = runtime.qt.eval(script)
        return {"url": runtime.current_url(), "elements": result or []}

    def click(self, p):
        runtime = self.runtime
        selector = p.get("selector")
        button = str(p.get("button") or "left")
        count = max(1, int(p.get("count") or 1))
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            if selector:
                locator = runtime.pw_page.locator(str(selector)).first
                box = locator.bounding_box()
                locator.click(button=button, click_count=count)
                if box:
                    runtime.cursor_x = int(box["x"] + box["width"] / 2)
                    runtime.cursor_y = int(box["y"] + box["height"] / 2)
                    runtime.cursor_visible = True
            else:
                x, y = runtime.viewport.point(p)
                runtime.pw_page.mouse.click(x, y, button=button, click_count=count)
                runtime.cursor_x, runtime.cursor_y = x, y
                runtime.cursor_visible = True
            runtime.playwright.refresh_frame()
        else:
            if selector:
                script = f"""(() => {{ const e=document.querySelector({json.dumps(str(selector))}); if(!e) return false; const r=e.getBoundingClientRect(); e.focus(); e.click(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}; }})()"""
                pos = runtime.qt.js(script)
                if not pos:
                    raise RuntimeError(f"Element not found: {selector}")
                runtime.cursor_x, runtime.cursor_y = int(pos["x"]), int(pos["y"])
                runtime.cursor_visible = True
            else:
                x, y = runtime.viewport.point(p)
                runtime.cursor_x, runtime.cursor_y = x, y
                runtime.cursor_visible = True
                runtime.qt.js(runtime.document.js_mouse_event(x, y, "click", button, count))
            runtime.qt.update_cursor()
        return runtime.current_state()

    def hover(self, p):
        runtime = self.runtime
        selector = p.get("selector")
        if selector:
            script = f"""(() => {{ const e=document.querySelector({json.dumps(str(selector))}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}}; }})()"""
            pos = runtime.qt.eval(script)
            if not pos:
                raise RuntimeError(f"Element not found: {selector}")
            x, y = int(pos["x"]), int(pos["y"])
        else:
            x, y = runtime.viewport.point(p)
        runtime.cursor_x, runtime.cursor_y = x, y
        runtime.cursor_visible = True
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.pw_page.mouse.move(x, y)
            runtime.playwright.refresh_frame()
        else:
            runtime.qt.js(runtime.document.js_mouse_event(x, y, "mousemove", "left", 0))
            runtime.qt.update_cursor()
        return runtime.current_state()

    def type(self, p):
        runtime = self.runtime
        selector = p.get("selector")
        text = str(p.get("text") or "")
        clear = bool(p.get("clear", False))
        enter = bool(p.get("press_enter", False))
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            target = runtime.pw_page.locator(str(selector)).first if selector else runtime.pw_page.locator(":focus")
            if selector:
                target.focus()
            if clear:
                target.fill("")
            target.type(text)
            if enter:
                target.press("Enter")
            runtime.playwright.refresh_frame()
        else:
            script = runtime.document.js_type(selector, text, clear, enter)
            ok = runtime.qt.js(script)
            if not ok:
                raise RuntimeError("No editable element is focused/found")
        return runtime.current_state()

    def key(self, p):
        runtime = self.runtime
        key = str(p.get("key") or "")
        if not key:
            raise ValueError("key is required")
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.pw_page.keyboard.press(key)
            runtime.playwright.refresh_frame()
        else:
            runtime.qt.js(runtime.document.js_key(key))
        return runtime.current_state()

    def scroll(self, p):
        runtime = self.runtime
        dx = int(p.get("dx") or 0)
        dy = int(p.get("dy") or 0)
        if p.get("x") is not None and p.get("y") is not None:
            runtime.cursor_x, runtime.cursor_y = runtime.viewport.point(p)
            runtime.cursor_visible = True
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.pw_page.mouse.move(runtime.cursor_x, runtime.cursor_y)
            runtime.pw_page.mouse.wheel(dx, dy)
            runtime.playwright.refresh_frame()
        else:
            runtime.qt.js(f"window.scrollBy({dx}, {dy}); true")
            runtime.qt.update_cursor()
        return runtime.current_state()

    def drag(self, p):
        runtime = self.runtime
        x1, y1 = runtime.viewport.clamp(int(p.get("x1")), int(p.get("y1")))
        x2, y2 = runtime.viewport.clamp(int(p.get("x2")), int(p.get("y2")))
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            runtime.pw_page.mouse.move(x1, y1)
            runtime.pw_page.mouse.down()
            runtime.pw_page.mouse.move(x2, y2, steps=12)
            runtime.pw_page.mouse.up()
            runtime.playwright.refresh_frame()
        else:
            script = f"""(() => {{
const a=document.elementFromPoint({x1},{y1}); const b=document.elementFromPoint({x2},{y2}); if(!a) return false;
for (const [t,x,y,buttons] of [['mousedown',{x1},{y1},1],['mousemove',{x2},{y2},1],['mouseup',{x2},{y2},0]]) {{
 const el=document.elementFromPoint(x,y)||a; el.dispatchEvent(new MouseEvent(t,{{bubbles:true,cancelable:true,clientX:x,clientY:y,buttons}}));
}} return true; }})()"""
            runtime.qt.js(script)
        runtime.cursor_x, runtime.cursor_y = x2, y2
        runtime.cursor_visible = True
        runtime.qt.update_cursor()
        return runtime.current_state()

    def wait(self, p):
        runtime = self.runtime
        selector = p.get("selector")
        timeout = max(0.1, min(float(p.get("timeout") or 10.0), 60.0))
        if selector:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if runtime.backend == "playwright":
                    runtime.playwright.ensure()
                    if runtime.pw_page.locator(str(selector)).count() > 0:
                        runtime.playwright.refresh_frame()
                        return runtime.current_state()
                elif runtime.qt.js(f"!!document.querySelector({json.dumps(str(selector))})"):
                    return runtime.current_state()
                # Keep the Qt event loop responsive while an agent waits for the DOM.
                runtime.qt.delay(0.1)
            raise TimeoutError(f"Selector not found: {selector}")
        seconds = max(0.0, min(float(p.get("seconds") or 1.0), 30.0))
        runtime.qt.delay(seconds)
        if runtime.backend == "playwright":
            runtime.playwright.refresh_frame()
        return runtime.current_state()

    def eval(self, p):
        runtime = self.runtime
        javascript = str(p.get("javascript") or "")
        if not javascript:
            raise ValueError("javascript is required")
        return {"url": runtime.current_url(), "result": runtime.qt.eval(javascript)}

    def select(self, p):
        runtime = self.runtime
        selector = str(p.get("selector") or "").strip()
        if not selector:
            raise ValueError("selector is required")
        value = p.get("value")
        label = p.get("label")
        index = p.get("index")
        if value is None and label is None and index is None:
            raise ValueError("value, label or index is required")
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            kwargs = {}
            if value is not None:
                kwargs["value"] = str(value)
            elif label is not None:
                kwargs["label"] = str(label)
            else:
                kwargs["index"] = int(index)
            selected = runtime.pw_page.locator(selector).first.select_option(**kwargs)
            runtime.playwright.refresh_frame()
            return {"selector": selector, "selected": selected, "url": runtime.current_url()}
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
        result = runtime.qt.js(script)
        if result is None:
            raise RuntimeError("Select element/option not found")
        return {"selector": selector, "selected": result, "url": runtime.current_url()}

    def check(self, p):
        runtime = self.runtime
        selector = str(p.get("selector") or "").strip()
        if not selector:
            raise ValueError("selector is required")
        checked = True if p.get("checked") is None else bool(p.get("checked"))
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            locator = runtime.pw_page.locator(selector).first
            if checked:
                locator.check()
            else:
                locator.uncheck()
            runtime.playwright.refresh_frame()
        else:
            script = f"""(() => {{ const e=document.querySelector({json.dumps(selector)}); if(!e || !('checked' in e)) return false;
            e.checked={str(checked).lower()}; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); return true; }})()"""
            if not runtime.qt.js(script):
                raise RuntimeError("Checkable element not found")
        return {"selector": selector, "checked": checked, "url": runtime.current_url()}

    def upload(self, p):
        runtime = self.runtime
        if runtime.backend != "playwright":
            raise RuntimeError("canvas_upload requires sandbox=true / Playwright backend")
        selector = str(p.get("selector") or "").strip()
        path = str(p.get("path") or "").strip()
        if not selector or not path:
            raise ValueError("selector and path are required")
        runtime.playwright.ensure()
        runtime.pw_page.locator(selector).first.set_input_files(path)
        runtime.playwright.refresh_frame()
        return {"selector": selector, "path": path, "url": runtime.current_url()}

    def console(self, p):
        runtime = self.runtime
        limit = max(1, min(int(p.get("limit") or 100), 1000))
        result = list(runtime.console[-limit:])
        if p.get("clear"):
            runtime.console.clear()
        return {"entries": result, "count": len(result)}

    def annotations(self, p):
        runtime = self.runtime
        result = list(runtime.annotations)
        if p.get("clear"):
            runtime.annotations.clear()
            runtime._render_annotations()
            runtime._notify_annotation_count_changed()
        return {"annotations": result, "count": len(result)}

    def clear_annotations(self):
        runtime = self.runtime
        count = len(runtime.annotations)
        runtime.annotations.clear()
        runtime._render_annotations()
        if count:
            runtime._notify_annotation_count_changed()
        return {"cleared": count}

    def server_start(self, p):
        runtime = self.runtime
        root = p.get("path") or p.get("__workdir") or os.getcwd()
        port = int(p.get("port") or 0)
        runtime.preview.start(root, port)
        result = runtime.preview.state()
        if p.get("open"):
            sandbox = True if p.get("sandbox") is None else bool(p.get("sandbox"))
            self.open({
                "url": runtime.server_url,
                "sandbox": sandbox,
                "__workdir": runtime.server_root,
                "__agent": bool(p.get("__agent")),
            })
            result["browser"] = runtime.current_state()
        return result

    def server_stop(self):
        runtime = self.runtime
        old = runtime.preview.state()
        runtime.preview.stop()
        old["running"] = False
        return old
