#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 02:00:00                  #
# ================================================== #
import time
import os

from PySide6.QtCore import Slot, QTimer

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):

    SLEEP_TIME = 1000  # 1 second

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_mouse_control"
        self.name = "Mouse And Keyboard"
        self.description = "Provides ability to control mouse and keyboard"
        self.prefix = "Mouse"
        self.order = 100
        self.allowed_cmds = [
            "open_web_browser",
            "get_mouse_position",
            "mouse_move",
            "mouse_drag",
            "mouse_click",
            "mouse_scroll",
            "get_screenshot",
            "keyboard_key",
            "keyboard_keys",
            "keyboard_type",
            "wait",
            "wait_5_seconds",
            "go_back",
            "go_forward",
            "search",
            "navigate",
            "click_at",
            "hover_at",
            "type_text_at",
            "key_combination",
            "scroll_document",
            "scroll_at",
            "drag_and_drop",
            "click",
            "double_click",
            "move",
            "type",
            "keypress",
            "scroll",
            "drag"
        ]
        self.use_locale = True
        self.worker = None
        self.config = Config(self)
        self.init_options()

        # Playwright sandbox context
        self.page = None
        self.pw = None
        self.browser = None
        self.context = None
        self.viewport_w = 1440
        self.viewport_h = 900

        # Pointer tracking for sandbox operations
        self.pointer_x = 0
        self.pointer_y = 0

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )
        elif name == Event.SYSTEM_PROMPT:
            if self.cmd_exe():
                data['value'] = self.on_system_prompt(data['value'])

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def is_sandbox(self) -> bool:
        """
        Check if sandbox mode is enabled

        :return: True if sandbox mode is enabled
        """
        return bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))

    def get_worker(self):
        """
        Get Worker instance based on sandbox option

        :return: Worker instance (native or sandboxed/Playwright)
        """
        if self.is_sandbox():
            from .worker_sandbox import Worker
            worker = Worker()
            worker.signals.start.connect(self.on_playwright_start)
            # Connect main-thread Playwright control channel
            worker.signals.call.connect(self.on_playwright_call)
            return worker
        from .worker import Worker
        return Worker()

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = self.get_worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    def handle_call(self, item: dict):
        """
        Handle call command
        This method is used to handle a single command call, typically from the agent

        :param item: command item to execute
        :return:
        """
        item["params"]["no_screenshot"] = True  # do not take screenshot for single command call
        worker = self.get_worker()
        worker.from_defaults(self)
        worker.cmds = [item]
        worker.ctx = CtxItem()
        worker.run()  # sync

    def is_google(self, ctx: CtxItem) -> bool:
        """
        Check if full response is required based on model provider

        :param ctx: context (CtxItem)
        :return: True if full response is required, False otherwise
        """
        model_id = ctx.model
        model_data = self.window.core.models.get(model_id) if model_id else None
        if model_data is not None:
            if model_data.provider == "google":
                return True
        return False

    @Slot(list, object, dict)
    def handle_finished_more(self, responses: list, ctx: CtxItem = None, extra_data: dict = None):
        """
        Handle finished responses signal

        :param responses: responses list
        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        # dispatch response (reply) - collect all responses and make screenshot only once at the end
        with_screenshot = True
        for response in responses:
            if ("result" in response
                    and "no_screenshot" in response["result"]
                    and response["result"]["no_screenshot"]):
                with_screenshot = False
            if ctx is not None:
                print("APPEND RESPONSE", response)
                self.prepare_reply_ctx(response, ctx)
                ctx.reply = True
        self.handle_delayed(ctx, with_screenshot)

    @Slot(object, bool)
    def handle_delayed(self, ctx: CtxItem, with_screenshot: bool = True):
        """
        Handle delayed screenshot

        :param ctx: context (CtxItem)
        :param with_screenshot: if True then take screenshot, otherwise just dispatch context
        """
        if self.get_option_value("allow_screenshot") and with_screenshot:
            QTimer.singleShot(self.SLEEP_TIME, lambda: self.delayed_screenshot(ctx))
            return

        context = BridgeContext()
        context.ctx = ctx
        extra = {}
        extra["response_type"] = "multiple"
        event = KernelEvent(KernelEvent.REPLY_ADD, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)

    def delayed_screenshot(self, ctx: CtxItem):
        """
        Delayed screenshot handler

        :param ctx: context (CtxItem)
        """
        self.window.controller.attachment.clear_silent()
        if self.is_sandbox():
            path = self.window.controller.painter.capture.screenshot_playwright(page=self.page, silent=True)  # Playwright screenshot
        else:
            path = self.window.controller.painter.capture.screenshot(attach_cursor=True, silent=True)  # attach screenshot
        if path:
            img_path = self.window.core.filesystem.make_local(path)
            ctx.images_before.append(img_path)
            context = BridgeContext()
            context.ctx = ctx
            event = KernelEvent(KernelEvent.REPLY_ADD, {
                'context': context,
                'extra': {},
            })
            self.window.dispatch(event)

    @Slot()
    def on_playwright_start(self):
        """
        Event: PLAYWRIGHT_START
        """
        self._ensure_browser()

    def _ensure_browser(self):
        """Start Playwright browser and page if not started yet."""
        if self.page:
            # check if browser is still connected
            try:
                self.page.screenshot()
                return
            except Exception as e:
                print(e)
                if self.page:
                    try:
                        self.page.close()
                    except Exception:
                        pass
                    self.page = None
                if self.browser:
                    try:
                        self.browser.close()
                    except Exception:
                        pass
                    self.browser = None
                if self.pw:
                    try:
                        self.pw.stop()
                    except Exception:
                        pass
                    self.pw = None
                if self.context:
                    try:
                        self.context.close()
                    except Exception:
                        pass
                    self.context = None


        # Playwright is required in sandbox mode
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            sync_playwright = None

        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed. Please install 'playwright' and the chosen browser.")

        # Determine headless and engine from plugin options if available
        headless = True
        engine = "chromium"
        try:
            if hasattr(self, "get_option_value"):
                hv = self.get_option_value("sandbox_headless")
                if hv is not None:
                    headless = bool(hv)
                ev = self.get_option_value("sandbox_browser")
                if ev in ("chromium", "firefox", "webkit"):
                    engine = ev
                vw = int(self.get_option_value("sandbox_viewport_w") or self.viewport_w)
                vh = int(self.get_option_value("sandbox_viewport_h") or self.viewport_h)
                self.viewport_w, self.viewport_h = vw, vh
        except Exception:
            pass

        args = []
        cfg_engine = self.get_option_value("sandbox_engine")
        if cfg_engine:
            engine = cfg_engine
        cfg_args = self.get_option_value("sandbox_args")
        if cfg_args:
            args = [arg.strip() for arg in cfg_args.split(",") if arg.strip()]
        cfg_path = self.get_option_value("sandbox_path")
        if cfg_path:
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = cfg_path
        err_msg = None
        if cfg_path and not (os.path.exists(cfg_path) and os.path.isdir(cfg_path)):
            err_msg = (f"Playwright browsers path does not exist: {cfg_path}\n\n"
                               f"1) Please install Playwright browser(s) on host machine: \n\n"
                               f"pip install playwright && playwright install {engine}\n\n"
                               f"2) Set path to browsers directory in `Mouse And Keyboard` plugin settings option: "
                               f"`Sandbox: Playwright browsers path`.")
        else:
            if os.environ.get("APPIMAGE") and not cfg_path:  # set path is required for AppImage version
                err_msg = (f"Playwright browsers path is not set - "
                                   f"1) Please install Playwright browser(s) on host machine: \n\n"
                                   f"pip install playwright && playwright install {engine}\n\n"
                                   f"2) Set path to browsers directory in `Mouse And Keyboard` plugin settings option: "
                                   f"`Sandbox: Playwright browsers path`.")

        if err_msg is not None:
            self.error(err_msg)
            raise RuntimeError(err_msg)

        self.pw = sync_playwright().start()
        launcher = getattr(self.pw, engine)
        self.browser = launcher.launch(
            headless=headless,
            args=args
        )
        self.context = self.browser.new_context(viewport={"width": self.viewport_w, "height": self.viewport_h})
        self.page = self.context.new_page()
        self.page.goto(self.get_option_value("sandbox_home"))

    # ========================= Playwright ops in main thread (from worker) ========================= #

    @Slot(str, dict, object, object)
    def on_playwright_call(self, op: str, params: dict, ret: dict, done):
        """
        Execute Playwright operation in the main (GUI) thread.
        'ret' is a mutable dict to fill with results. 'done' is a threading.Event to signal completion.
        """
        try:
            # Always ensure browser exists before any operation
            if op in ("ensure", "navigate", "go_back", "go_forward", "move", "click",
                      "scroll", "drag", "keypress", "keypress_combo", "type",
                      "screenshot", "click_at", "hover_at", "type_text_at"):
                self._ensure_browser()

            if op == "ensure":
                vw, vh = self._get_viewport()
                ret.update({"ok": True, "viewport_w": vw, "viewport_h": vh, "url": self._get_url(),
                            "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "navigate":
                url = str(params.get("url", "") or "")
                if url:
                    self.page.goto(url, wait_until="load")
                self._wait_for_load()
                vw, vh = self._get_viewport()
                ret.update({"ok": True, "url": self._get_url(), "viewport_w": vw, "viewport_h": vh,
                            "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "go_back":
                self.page.go_back(wait_until="load")
                vw, vh = self._get_viewport()
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "viewport_w": vw, "viewport_h": vh,
                            "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "go_forward":
                self.page.go_forward(wait_until="load")
                self._wait_for_load()
                vw, vh = self._get_viewport()
                ret.update({"ok": True, "url": self._get_url(), "viewport_w": vw, "viewport_h": vh,
                            "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "move":
                x = int(params.get("x"))
                y = int(params.get("y"))
                self.page.mouse.move(x, y)
                self.pointer_x, self.pointer_y = x, y
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": x, "mouse_y": y})

            elif op == "click":
                button = str(params.get("button", "left")).lower()
                count = int(params.get("count", 1))
                x = params.get("x", None)
                y = params.get("y", None)
                if x is None or y is None:
                    x, y = self.pointer_x, self.pointer_y
                else:
                    x, y = int(x), int(y)
                    self.page.mouse.move(x, y)
                    self.pointer_x, self.pointer_y = x, y
                self.page.mouse.click(x, y, button=button, click_count=max(1, count))
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": x, "mouse_y": y})

            elif op == "click_at":
                x = int(params.get("x"))
                y = int(params.get("y"))
                button = str(params.get("button", "left")).lower()
                count = int(params.get("count", 1))
                self.page.mouse.move(x, y)
                self.pointer_x, self.pointer_y = x, y
                self.page.mouse.click(x, y, button=button, click_count=max(1, count))
                self._wait_for_load()
                print("cliecked at", x, y)
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": x, "mouse_y": y})

            elif op == "hover_at":
                x = int(params.get("x"))
                y = int(params.get("y"))
                self.page.mouse.move(x, y)
                self.pointer_x, self.pointer_y = x, y
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": x, "mouse_y": y})

            elif op == "type_text_at":
                x = int(params.get("x"))
                y = int(params.get("y"))
                text = str(params.get("text", "") or "")
                press_enter = bool(params.get("press_enter", True))
                clear_before = bool(params.get("clear_before_typing", True))
                # Focus target
                self.page.mouse.move(x, y)
                self.pointer_x, self.pointer_y = x, y
                self.page.mouse.click(x, y, button="left", click_count=1)
                # Optional clear
                if clear_before:
                    # Use Control+A universally; adjust if needed for macOS
                    self._press_combo(["Control", "a"])
                    self.page.keyboard.press("Backspace")
                # Type
                if text:
                    self.page.keyboard.type(text)
                if press_enter:
                    self.page.keyboard.press("Enter")
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "scroll":
                x = params.get("x", None)
                y = params.get("y", None)
                if x is not None and y is not None:
                    xx, yy = int(x), int(y)
                    self.page.mouse.move(xx, yy)
                    self.pointer_x, self.pointer_y = xx, yy
                dx = int(params.get("dx", 0))
                dy = int(params.get("dy", 0))
                self.page.mouse.wheel(dx, dy)
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "drag":
                x = int(params.get("x"))
                y = int(params.get("y"))
                dx = int(params.get("dx"))
                dy = int(params.get("dy"))
                self.page.mouse.move(x, y)
                self.pointer_x, self.pointer_y = x, y
                self.page.mouse.down(button="left")
                self.page.mouse.move(dx, dy, steps=12)
                self.page.mouse.up(button="left")
                self.pointer_x, self.pointer_y = dx, dy
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "keypress":
                key = str(params.get("key"))
                self.page.keyboard.press(self._key_to_playwright(key))
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "keypress_combo":
                keys = params.get("keys", []) or []
                if isinstance(keys, str):
                    keys = [p.strip() for p in keys.replace("+", " ").split() if p.strip()]
                self._press_combo(keys)
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "type":
                text = str(params.get("text", "") or "")
                modifier = params.get("modifier", None)
                if modifier:
                    mod = self._key_to_playwright(modifier)
                    self.page.keyboard.down(mod)
                    try:
                        self.page.keyboard.type(text)
                    finally:
                        self.page.keyboard.up(mod)
                else:
                    self.page.keyboard.type(text)
                self._wait_for_load()
                ret.update({"ok": True, "url": self._get_url(), "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            elif op == "screenshot":
                full = bool(params.get("full_page", False))
                img_bytes = self.page.screenshot(full_page=full)
                vw, vh = self._get_viewport()
                ret.update({"ok": True, "image": img_bytes, "url": self._get_url(),
                            "viewport_w": vw, "viewport_h": vh,
                            "mouse_x": self.pointer_x, "mouse_y": self.pointer_y})

            else:
                ret.update({"ok": False, "error": f"Unknown op: {op}", "url": self._get_url()})

        except Exception as e:
            ret.update({"ok": False, "error": str(e), "url": self._get_url()})
        finally:
            try:
                done.set()
            except Exception:
                pass

    def _wait_for_load(self, timeout: int = 5000):
        """Wait for page load state."""
        if self.page:
            self.page.wait_for_load_state(timeout=timeout)
        time.sleep(1)

    # ========================= Helpers for Playwright ops ========================= #

    def get_last_url(self):
        """
        Get current page URL

        :return: URL string
        """
        return self._get_url()

    def _get_url(self) -> str:
        try:
            if self.page:
                return self.page.url or ""
        except Exception:
            return ""
        return ""

    def _get_viewport(self):
        try:
            if self.page:
                vp = self.page.viewport_size
                if callable(vp):
                    vp = self.page.viewport_size()
                if isinstance(vp, dict) and "width" in vp and "height" in vp:
                    self.viewport_w = int(vp["width"])
                    self.viewport_h = int(vp["height"])
        except Exception:
            pass
        return self.viewport_w, self.viewport_h

    def _key_to_playwright(self, key: str) -> str:
        mapping = {
            "PAGEDOWN": "PageDown",
            "PAGEUP": "PageUp",
            "BACKSPACE": "Backspace",
            "RETURN": "Enter",
            "ENTER": "Enter",
            "ESCAPE": "Escape",
            "ESC": "Escape",
            "LEFT": "ArrowLeft",
            "RIGHT": "ArrowRight",
            "UP": "ArrowUp",
            "DOWN": "ArrowDown",
            "SPACE": " ",
            "TAB": "Tab",
            "CTRL": "Control",
            "CONTROL": "Control",
            "ALT": "Alt",
            "SHIFT": "Shift",
            "CMD": "Meta",
            "SUPER": "Meta",
            "START": "Meta",
            "PRINTSCREEN": "PrintScreen",
            "PRINT_SCREEN": "PrintScreen",
            "PRTSC": "PrintScreen",
            "END": "End",
            "HOME": "Home",
            "DELETE": "Delete",
            "INSERT": "Insert",
        }
        u = key.upper() if isinstance(key, str) else key
        if u in mapping:
            return mapping[u]
        if isinstance(u, str) and len(u) == 2 and u[0] == "F" and u[1].isdigit():
            return u
        if isinstance(u, str) and len(u) == 3 and u[0] == "F" and u[1:].isdigit():
            return u
        return key

    def _press_combo(self, keys, delay: float = 0.0):
        if not keys:
            return
        # Try chord, e.g., "Control+L"
        if len(keys) >= 2:
            chord = "+".join(self._key_to_playwright(k) for k in keys)
            try:
                self.page.keyboard.press(chord, delay=delay)
                return
            except Exception:
                pass
        # Fallback: modifier down/up sequence
        modifiers = {"Control", "Alt", "Shift", "Meta"}
        downs = []
        try:
            for k in keys:
                pk = self._key_to_playwright(k)
                if pk in modifiers and pk not in downs:
                    self.page.keyboard.down(pk)
                    downs.append(pk)
                else:
                    self.page.keyboard.press(pk, delay=delay)
        finally:
            for m in reversed(downs):
                self.page.keyboard.up(m)

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        if prompt is not None and prompt.strip() != "":
            prompt += "\n\n"
        return prompt + self.get_option_value("prompt")