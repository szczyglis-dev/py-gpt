#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 18:40:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "canvas_web"
        self.is_common_plugin = True
        self.name = "Canvas"
        self.description = (
            "BETA. Provides an internal browser/canvas runtime for HTML, JavaScript, website prototyping, "
            "scoped browser computer-use, Playwright sandbox automation, annotations and a lightweight preview server. "
            "This feature will be expanded in future releases."
        )
        self.prefix = "Canvas/Web"
        self.order = 100
        self.use_locale = True
        self.tabs = {
            "browser": "Browser",
            "sandbox": "Playwright",
            "annotations": "Annotations",
            "server": "Preview server",
            "tools": "Tools",
        }
        self.allowed_cmds = [
            "canvas_open", "canvas_change_resolution", "canvas_set_html",
            "canvas_get_html", "canvas_current", "canvas_close",
            "canvas_prev", "canvas_next", "canvas_reload", "canvas_screenshot",
            "canvas_inspect", "canvas_click", "canvas_hover", "canvas_type",
            "canvas_key", "canvas_scroll", "canvas_drag", "canvas_wait",
            "canvas_eval", "canvas_select", "canvas_check", "canvas_upload",
            "canvas_console", "canvas_annotations",
            "canvas_clear_annotations", "web_server_start", "web_server_current", "web_server_stop",
        ]
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        name = event.name
        data = event.data
        ctx = event.ctx
        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)
        elif name == Event.CMD_EXECUTE:
            self.cmd(ctx, data.get("commands", []))
        elif name == Event.SYSTEM_PROMPT:
            if self.cmd_exe():
                data["value"] = self.on_system_prompt(data.get("value", ""))
        elif name == Event.POST_PROMPT_END:
            if ctx is not None and (ctx.reply or data.get("reply")):
                return
            if self.cmd_exe() and self.get_option_value("annotation_prompt"):
                data["value"] = self.append_runtime_context(data.get("value", ""))

    def cmd_syntax(self, data: dict):
        for name in self.allowed_cmds:
            if self.has_cmd(name):
                data["cmd"].append(self.get_cmd(name))

    @staticmethod
    def normalize_cmd_name(name: str) -> str:
        # Backward compatibility for conversations/tool calls created before the
        # public command prefix was renamed from web_browser_* to canvas_*.
        if isinstance(name, str) and name.startswith("web_browser_"):
            return "canvas_" + name[len("web_browser_"):]
        return name

    def cmd(self, ctx: CtxItem, cmds: list):
        from .worker import Worker

        selected = []
        for item in cmds:
            name = self.normalize_cmd_name(item.get("cmd"))
            if name not in self.allowed_cmds:
                continue
            normalized = dict(item)
            normalized["cmd"] = name
            selected.append(normalized)
        if not selected:
            return
        self.cmd_prepare(ctx, selected)
        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = selected
            worker.ctx = ctx
            if not self.is_async(ctx) or ctx.async_disabled:
                worker.run()
            else:
                worker.run_async()
        except Exception as exc:
            self.report_runtime_error(exc)

    def report_runtime_error(self, exc):
        """Log Canvas/Web runtime errors without interrupting the user with dialogs."""
        msg = str(exc)
        reported = False
        try:
            tool = self.window.tools.get("web_browser")
            if tool is not None:
                # _append_console also mirrors error-level entries to the app log
                # and bottom status bar. Keep one canonical reporting path.
                tool._append_console("runtime", "error", msg)
                reported = True
        except Exception:
            pass
        if reported:
            return
        try:
            self.window.core.debug.log(exc)
        except Exception:
            pass
        try:
            self.window.update_status(f"{self.name}: {msg}")
        except Exception:
            pass

    @Slot(object)
    def handle_error(self, err):
        # Browser/DOM/JavaScript interaction failures are expected operational
        # outcomes (e.g. a selector disappearing). Keep them in logs/status and
        # return the error to the model; do not open an alert dialog.
        self.report_runtime_error(err)

    @Slot(str, dict, object, object)
    def on_browser_call(self, cmd: str, params: dict, ret: dict, done):
        try:
            tool = self.window.tools.get("web_browser")
            if tool is None:
                raise RuntimeError("Canvas/web browser tool is not registered")
            ret["result"] = tool.runtime_call(cmd, params, plugin=self)
        except Exception as exc:
            ret["error"] = str(exc)
            self.report_runtime_error(exc)
        finally:
            done.set()

    def attach_screenshot_to_ctx(self, ctx: CtxItem, path: str):
        if ctx is None or not path:
            return
        try:
            local = self.window.core.filesystem.make_local(path, ctx=ctx)
            if not isinstance(getattr(ctx, "images_before", None), list):
                ctx.images_before = []
            if local not in ctx.images_before:
                ctx.images_before.append(local)
        except Exception as exc:
            self.window.core.debug.log(exc)

    def on_system_prompt(self, prompt: str) -> str:
        text = """
# Canvas/web browser, HTML and JavaScript runtime

You have a dedicated PyGPT canvas/web browser runtime. Use it for building and testing websites, HTML/CSS/JS prototypes, canvas-based interfaces and small browser applications. Tools prefixed with `canvas_` control this canvas/web browser. It is separate from the user's desktop mouse and keyboard.

Canvas/web browser mouse and keyboard tools are scoped only to this viewport and use a virtual model cursor. Do not use global OS mouse/keyboard control for work that can be completed inside the canvas/web browser. The default backend is the built-in QWebEngine browser. Playwright is opt-in and is available only when the user enables `Use sandbox (Playwright)` in this plugin's settings; do not assume Playwright is enabled. The `sandbox` argument may request Playwright only when that master setting is on.

Use `canvas_inspect` before coordinate clicking when possible; returned `data-pygpt-ref` selectors are more reliable than vision coordinates. Use `canvas_screenshot` whenever visual verification matters. Use `canvas_set_html` to render complete HTML/CSS/JS directly in the canvas/web browser, with relative assets resolved from its base URL/work directory. Use `canvas_get_html` when you need the current rendered document source. `canvas_close` closes the visible canvas tab in the PyGPT application; it does not destroy the background canvas/web browser runtime.

For local websites use `web_server_start`; it serves only on loopback and defaults to the current PyGPT work/data directory. Open or inspect that local site through the `canvas_*` tools.

User annotations made from the canvas/web browser context menu are authoritative feedback about the displayed prototype/page. Read and apply them before making further UI changes.
""".strip()
        if prompt and prompt.strip():
            return prompt.rstrip() + "\n\n" + text
        return text

    def append_runtime_context(self, prompt: str) -> str:
        try:
            tool = self.window.tools.get("web_browser")
            if tool is None:
                return prompt
            annotations = tool.get_annotations()
            if not annotations:
                return prompt
            lines = ["CANVAS/WEB BROWSER USER ANNOTATIONS (current runtime):"]
            for item in annotations[-20:]:
                parts = [f"- #{item.get('id')}"]
                if item.get("url"):
                    parts.append(f"URL={item['url']}")
                if item.get("selection"):
                    parts.append(f"selection={item['selection']!r}")
                if item.get("element"):
                    parts.append(f"element={item['element']}")
                if item.get("note"):
                    parts.append(f"note={item['note']!r}")
                lines.append("; ".join(parts))
            block = "\n".join(lines)
            if prompt and prompt.strip():
                return prompt.rstrip() + "\n\n" + block
            return block
        except Exception as exc:
            self.window.core.debug.log(exc)
            return prompt
