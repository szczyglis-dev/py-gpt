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
import re
from pathlib import Path
from urllib.parse import urljoin
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QFileDialog
from pygpt_net.utils import trans


class CanvasDocument:
    """Load, save and serialize documents and resolve their asset URLs."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.revision = 0

    def selected_text(self) -> str:
        """Return selected text from the active Canvas backend."""
        runtime = self.runtime
        try:
            if runtime.backend == "playwright":
                runtime.playwright.ensure()
                return str(runtime.pw_page.evaluate(r"""() => {
                    const el = document.activeElement;
                    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')
                            && typeof el.selectionStart === 'number' && typeof el.selectionEnd === 'number') {
                        return String(el.value || '').slice(el.selectionStart, el.selectionEnd);
                    }
                    return window.getSelection ? String(window.getSelection()) : '';
                }""") or "")
            if runtime.surface is not None and runtime.surface.web.page().hasSelection():
                return str(runtime.surface.web.page().selectedText() or "")
        except Exception as exc:
            try:
                runtime.window.core.debug.log(exc)
            except Exception:
                pass
        return ""

    def open_file(self):
        """Load an HTML file from disk into the current Canvas runtime."""
        runtime = self.runtime
        last_dir = runtime.window.core.config.get_last_used_dir()
        path, _ = QFileDialog.getOpenFileName(
            runtime.window,
            trans("ui.open_html", domain="plugin.canvas_web"),
            last_dir,
            "HTML files (*.html *.htm);;All files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                html = handle.read()
            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(path)) + os.sep).toString()
            runtime.window.core.config.set_last_used_dir(os.path.dirname(path))
            source_visible = bool(runtime.surface is not None and getattr(runtime.surface, "_source_visible", False))
            runtime.runtime_call("canvas_set_html", {
                "html": html,
                "base_url": base_url,
                "__workdir": os.path.dirname(os.path.abspath(path)),
                "__ui": True,
            })
            if source_visible and runtime.surface is not None:
                runtime.surface.show_source(html, base_url=base_url)
            runtime.window.update_status(f"{trans('action.open')}: {os.path.basename(path)}")
        except Exception as exc:
            runtime.append_console("file", "error", str(exc))

    def save_file(self):
        """Save the currently rendered/edited Canvas HTML document to disk."""
        runtime = self.runtime
        last_dir = runtime.window.core.config.get_last_used_dir()
        path, _ = QFileDialog.getSaveFileName(
            runtime.window,
            trans("ui.save_html", domain="plugin.canvas_web"),
            last_dir,
            "HTML files (*.html *.htm);;All files (*)",
            "HTML files (*.html *.htm)",
        )
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".html"
        try:
            if runtime.surface is not None and getattr(runtime.surface, "_source_visible", False):
                html = runtime.surface.source.toPlainText()
            else:
                html = str(runtime.qt.eval(runtime.JS_SERIALIZE_HTML) or runtime.runtime_html or "")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(html)
            runtime.window.core.config.set_last_used_dir(os.path.dirname(path))
            runtime.window.update_status(f"{trans('status.saved')}: {os.path.basename(path)}")
        except Exception as exc:
            runtime.append_console("file", "error", str(exc))

    def show_source(self):
        """Switch the persistent viewport to editable serialized page source.

        QWebEngine serialization is asynchronous on purpose. Running a nested
        event loop from inside the WebEngine context menu can leave the menu
        active while Chromium waits for the GUI loop, which made Show source
        appear to do nothing on some platforms.
        """
        runtime = self.runtime
        runtime.viewport.ensure_surface()
        current = str(runtime.current_url() or "")
        current_qurl = QUrl(current)
        entry = None
        if 0 <= runtime.canvas_history_index < len(runtime.canvas_history):
            entry = runtime.canvas_history[runtime.canvas_history_index]
        if isinstance(entry, dict) and entry.get("kind") == "html":
            # set_html under Playwright is served from a loopback URL. Preserve
            # the document's original base URL instead of leaking that runtime
            # transport URL into later Source edits/reloads.
            url = str(entry.get("base_url") or runtime.base_url or "")
            # Submitted code is authoritative for synthetic documents. DOM
            # serialization can contain animation state and stale callbacks.
            runtime.surface.show_source(str(entry.get("html") or ""), base_url=url)
            return
        else:
            url = current if current_qurl.scheme() in ("http", "https", "file") else str(runtime.base_url or "")
        if runtime.backend == "playwright":
            runtime.playwright.ensure()
            html = str(runtime.pw_page.evaluate(runtime.JS_SERIALIZE_HTML) or runtime.runtime_html or "")
            runtime.surface.show_source(html, base_url=url)
            return

        page = runtime.surface.web.page()
        revision = self.revision

        def ready(html):
            if runtime.surface is None or self.revision != revision:
                return
            text = str(html or runtime.runtime_html or "")
            runtime.surface.show_source(text, base_url=url)

        page.runJavaScript(runtime.JS_SERIALIZE_HTML, 0, ready)

    def show_canvas(self):
        """Return from source editor to the rendered Canvas/HTML viewport."""
        runtime = self.runtime
        if runtime.surface is not None:
            runtime.surface.show_canvas()

    def apply_source(self, html: str, base_url: str = ""):
        """Apply an edit from source view to the same browser runtime."""
        runtime = self.runtime
        params = {
            "html": str(html or ""),
            "base_url": base_url or runtime.base_url or "",
            "__ui": True,
            "__source_edit": True,
        }
        result = runtime.commands.set_html(params)
        runtime.notify_state()
        return result

    @staticmethod
    def has_explicit_scheme(value: str) -> bool:
        # Generic RFC-style scheme detection covers http(s), file, about, data,
        # ftp, ws(s), mailto and future/custom schemes without maintaining a list.
        return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", str(value or "")))

    @staticmethod
    def looks_like_direct_address(value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if CanvasDocument.has_explicit_scheme(text):
            return True
        if text.startswith(("/", "./", "../", "~/", "\\\\")):
            return True
        if re.match(r"^[A-Za-z]:[\\/]", text):
            return True

        expanded = os.path.expanduser(text)
        try:
            if Path(expanded).exists():
                return True
        except (OSError, ValueError):
            pass

        # Browser-like convenience: domain names, localhost and literal IPs can
        # be typed without a protocol; only genuine free text becomes a search.
        if any(ch.isspace() for ch in text):
            return False
        host = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        host_no_port = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
        lowered = host_no_port.lower()
        if lowered == "localhost":
            return True
        if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", host_no_port):
            return True
        if host.startswith("[") and "]" in host:  # IPv6 literal
            return True
        return "." in host_no_port and not host_no_port.startswith(".")

    def address_target(self, value: str) -> str:
        runtime = self.runtime
        text = str(value or "").strip()
        if not text:
            return ""
        if self.looks_like_direct_address(text):
            return text
        return runtime.search_engine().build_url(text)

    def resolve_url(self, value: str, workdir=None):
        runtime = self.runtime
        value = (value or "").strip()
        if not value:
            return ""
        if runtime.server_url and not QUrl(value).scheme() and not os.path.isabs(value):
            local_candidate = os.path.join(runtime.server_root or "", value)
            if os.path.exists(local_candidate):
                return urljoin(runtime.server_url, value.replace(os.sep, "/"))
        path = Path(os.path.expanduser(value))
        if not path.is_absolute() and workdir:
            path = Path(workdir) / path
        if path.exists():
            return QUrl.fromLocalFile(str(path.resolve())).toString()
        qurl = QUrl.fromUserInput(value)
        return qurl.toString()

    @staticmethod
    def normalize_base_url(base_url, workdir):
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
    def inject_base(html, base_url):
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

    @staticmethod
    def js_mouse_event(x, y, event_type, button, count):
        button_map = {"left": 0, "middle": 1, "right": 2}
        btn = button_map.get(button, 0)
        return f"""(() => {{ const e=document.elementFromPoint({x},{y}); if(!e) return false;
e.dispatchEvent(new MouseEvent({json.dumps(event_type)},{{bubbles:true,cancelable:true,clientX:{x},clientY:{y},button:{btn},detail:{count}}}));
if({json.dumps(event_type)}==='click' && e.focus) e.focus(); return true; }})()"""

    @staticmethod
    def js_type(selector, text, clear, enter):
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
    def js_key(key):
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
