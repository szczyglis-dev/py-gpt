#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 18:35:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        plugin.add_option(
            "use_sandbox", type="bool", value=False,
            label="Use sandbox (Playwright)",
            description="Enable the isolated Playwright browser backend. When disabled, Canvas and HTML always uses the built-in QWebEngine browser and does not try to launch Playwright.",
            tab="sandbox")
        plugin.add_option(
            "playwright_engine", type="combo", value="chromium",
            label="Playwright engine", description="Browser engine used by the isolated Playwright backend.",
            keys=[{"chromium": "Chromium"}, {"firefox": "Firefox"}, {"webkit": "WebKit"}], tab="sandbox")
        plugin.add_option(
            "playwright_path", type="text", value="",
            label="Playwright browsers directory",
            description="Optional PLAYWRIGHT_BROWSERS_PATH. Leave empty to use the Playwright default.", tab="sandbox")
        plugin.add_option(
            "playwright_args", type="text", value="",
            label="Playwright browser args",
            description="Optional comma-separated launch arguments for Chromium/Playwright.", tab="sandbox", advanced=True)
        plugin.add_option(
            "default_width", type="int", value=1280, label="Default viewport width",
            description="Default browser viewport width in pixels.", min=320, max=7680, tab="browser")
        plugin.add_option(
            "default_height", type="int", value=800, label="Default viewport height",
            description="Default browser viewport height in pixels.", min=240, max=4320, tab="browser")
        plugin.add_option(
            "auto_open_split", type="bool", value=True, label="Auto-open browser in split screen",
            description="On the first agent browser open in an application session, create/focus the Canvas and HTML tab in the second column and reveal split screen. If the user hides split screen afterwards, it is not forced open again in the same app session.", tab="browser")
        plugin.add_option(
            "annotation_prompt", type="bool", value=True, label="Expose user annotations to the model",
            description="Append pending browser/canvas annotations to the runtime system prompt.", tab="annotations")
        plugin.add_option(
            "max_annotations", type="int", value=30, label="Maximum annotations",
            description="Maximum annotations retained in the current browser session.", min=1, max=200, tab="annotations")
        plugin.add_option(
            "console_limit", type="int", value=200, label="Console log limit",
            description="Maximum browser console entries retained in memory.", min=10, max=2000, tab="browser", advanced=True)

        def cmd(name, instruction, params, description=None, tab="tools"):
            plugin.add_cmd(name, instruction=instruction, params=params, enabled=True,
                           description=description or instruction, tab=tab)

        cmd("canvas_open",
            "Open or navigate the canvas/web browser runtime. Input is scoped to this canvas viewport only. "
            "The plugin setting 'Use sandbox (Playwright)' is the master switch for Playwright; when it is disabled, "
            "this command always uses QWebEngine even if sandbox=true is requested. resolution may be '1280x800', "
            "'390x844', or omitted.", [
                {"name": "url", "type": "str", "description": "URL, file path or relative path to open", "required": False},
                {"name": "resolution", "type": "str", "description": "Optional WIDTHxHEIGHT, e.g. 1280x800 or 390x844", "required": False},
                {"name": "sandbox", "type": "bool", "description": "Request the isolated Playwright backend when the plugin setting 'Use sandbox (Playwright)' is enabled. Otherwise this is ignored and QWebEngine is used.", "required": False},
            ])
        cmd("canvas_change_resolution",
            "Change the canvas/web browser viewport. orientation=portrait keeps the shorter edge as width; landscape keeps the longer edge as width.", [
                {"name": "width", "type": "int", "description": "Viewport width", "required": True},
                {"name": "height", "type": "int", "description": "Viewport height", "required": True},
                {"name": "orientation", "type": "str", "description": "auto|portrait|landscape", "required": False},
            ])
        cmd("canvas_set_html",
            "Render arbitrary HTML/CSS/JavaScript in the current canvas/web browser runtime. Relative assets resolve against base_url; when omitted, the current PyGPT data/work directory is used.", [
                {"name": "html", "type": "str", "description": "HTML/CSS/JS document", "required": True},
                {"name": "base_url", "type": "str", "description": "Optional base URL or local directory", "required": False},
            ])
        cmd("canvas_get_html", "Get the current canvas/web browser URL and serialized HTML document.", [])
        cmd("canvas_current", "Get the current canvas/web browser runtime state: URL, title, backend, viewport, history, virtual cursor, UI surface, server and annotations.", [])
        cmd("canvas_close", "Close the canvas tab in the PyGPT application. This closes the visible canvas UI only; it does not destroy the background canvas/web browser runtime session.", [])
        cmd("canvas_prev", "Navigate the canvas/web browser to the previous history entry.", [])
        cmd("canvas_next", "Navigate the canvas/web browser to the next history entry.", [])
        cmd("canvas_reload", "Reload the current canvas/web browser document.", [])
        cmd("canvas_screenshot",
            "Capture the current canvas/web browser viewport including the model's virtual cursor. The screenshot is attached to the current tool context so vision-capable models can inspect it.", [
                {"name": "path", "type": "str", "description": "Optional output path", "required": False},
                {"name": "full_page", "type": "bool", "description": "Full page when Playwright backend is active", "required": False},
            ])
        cmd("canvas_inspect",
            "Inspect the canvas/web browser DOM. By default returns visible interactive elements with stable data-pygpt-ref selectors, labels, text and bounding boxes. Use before coordinate clicking whenever possible.", [
                {"name": "selector", "type": "str", "description": "Optional CSS selector; omit for interactive elements", "required": False},
                {"name": "limit", "type": "int", "description": "Maximum elements", "required": False},
            ])
        cmd("canvas_click",
            "Click inside the canvas/web browser only. Prefer selector/ref from canvas_inspect; coordinates are viewport pixels.", [
                {"name": "selector", "type": "str", "description": "CSS selector or [data-pygpt-ref=...]", "required": False},
                {"name": "x", "type": "int", "description": "Viewport X", "required": False},
                {"name": "y", "type": "int", "description": "Viewport Y", "required": False},
                {"name": "button", "type": "str", "description": "left|middle|right", "required": False},
                {"name": "count", "type": "int", "description": "Click count", "required": False},
            ])
        cmd("canvas_hover", "Move the model's virtual cursor/hover inside the canvas/web browser viewport.", [
                {"name": "selector", "type": "str", "description": "Optional CSS selector", "required": False},
                {"name": "x", "type": "int", "description": "Viewport X", "required": False},
                {"name": "y", "type": "int", "description": "Viewport Y", "required": False},
            ])
        cmd("canvas_type", "Focus an element and type text in the canvas/web browser.", [
                {"name": "selector", "type": "str", "description": "Optional CSS selector; otherwise currently focused element", "required": False},
                {"name": "text", "type": "str", "description": "Text to type", "required": True},
                {"name": "clear", "type": "bool", "description": "Clear existing value first", "required": False},
                {"name": "press_enter", "type": "bool", "description": "Press Enter after typing", "required": False},
            ])
        cmd("canvas_key", "Send a keyboard key/chord to the canvas/web browser only, e.g. Enter, Escape, Tab, Control+A.", [
                {"name": "key", "type": "str", "description": "Key or Playwright-style chord", "required": True},
            ])
        cmd("canvas_scroll", "Scroll the canvas/web browser. dx/dy are CSS/viewport pixels; positive dy scrolls down.", [
                {"name": "dx", "type": "int", "description": "Horizontal delta", "required": False},
                {"name": "dy", "type": "int", "description": "Vertical delta", "required": False},
                {"name": "x", "type": "int", "description": "Optional pointer X before scroll", "required": False},
                {"name": "y", "type": "int", "description": "Optional pointer Y before scroll", "required": False},
            ])
        cmd("canvas_drag", "Drag inside the canvas/web browser from one viewport point to another.", [
                {"name": "x1", "type": "int", "description": "Start X", "required": True},
                {"name": "y1", "type": "int", "description": "Start Y", "required": True},
                {"name": "x2", "type": "int", "description": "End X", "required": True},
                {"name": "y2", "type": "int", "description": "End Y", "required": True},
            ])
        cmd("canvas_wait", "Wait for a selector or a short amount of time inside the canvas/web browser runtime.", [
                {"name": "seconds", "type": "float", "description": "Seconds to wait when selector is omitted", "required": False},
                {"name": "selector", "type": "str", "description": "Optional CSS selector to wait for", "required": False},
                {"name": "timeout", "type": "float", "description": "Selector timeout in seconds", "required": False},
            ])
        cmd("canvas_eval", "Evaluate JavaScript in the current canvas/web browser page and return a JSON-serializable result. Execution is scoped to that page.", [
                {"name": "javascript", "type": "str", "description": "JavaScript expression or function body", "required": True},
            ])
        cmd("canvas_select", "Select an option in a <select> element in the canvas/web browser and dispatch normal input/change events.", [
                {"name": "selector", "type": "str", "description": "CSS selector for the select element", "required": True},
                {"name": "value", "type": "str", "description": "Option value", "required": False},
                {"name": "label", "type": "str", "description": "Visible option label", "required": False},
                {"name": "index", "type": "int", "description": "Zero-based option index", "required": False},
            ])
        cmd("canvas_check", "Set a checkbox/radio state in the canvas/web browser.", [
                {"name": "selector", "type": "str", "description": "CSS selector", "required": True},
                {"name": "checked", "type": "bool", "description": "Desired checked state; defaults to true", "required": False},
            ])
        cmd("canvas_upload", "Upload a host file into an <input type=file> in the canvas/web browser. This is Playwright-only and the path is validated by PyGPT file security before use.", [
                {"name": "selector", "type": "str", "description": "CSS selector for input[type=file]", "required": True},
                {"name": "path", "type": "str", "description": "File path", "required": True},
            ])
        cmd("canvas_console", "Get recent JavaScript console messages and page errors from the canvas/web browser.", [
                {"name": "clear", "type": "bool", "description": "Clear stored console after reading", "required": False},
                {"name": "limit", "type": "int", "description": "Maximum entries returned", "required": False},
            ])
        cmd("canvas_annotations", "Get annotations/selections explicitly left by the user on the current canvas/web browser session.", [
                {"name": "clear", "type": "bool", "description": "Clear annotations after reading", "required": False},
            ], tab="annotations")
        cmd("canvas_clear_annotations", "Clear all canvas/web browser annotations.", [], tab="annotations")
        cmd("web_server_start",
            "Start a lightweight loopback-only static HTTP server rooted in a directory. Use it to preview websites/apps from the PyGPT working directory in the canvas/web browser without adding another package.", [
                {"name": "path", "type": "str", "description": "Directory to serve; defaults to current PyGPT data/work directory", "required": False},
                {"name": "port", "type": "int", "description": "Loopback port, 0 chooses a free port", "required": False},
                {"name": "open", "type": "bool", "description": "Open the server root in the canvas/web browser", "required": False},
                {"name": "sandbox", "type": "bool", "description": "Use Playwright if opening the server", "required": False},
            ], tab="server")
        cmd("web_server_current", "Get current lightweight preview server state and base URL.", [], tab="server")
        cmd("web_server_stop", "Stop the lightweight preview server.", [], tab="server")
