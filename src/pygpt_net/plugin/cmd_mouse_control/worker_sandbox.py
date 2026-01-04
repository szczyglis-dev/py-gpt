#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import time
import threading
from typing import Optional, List

from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSandboxSignals(BaseSignals):
    screenshot = Signal(dict, object)
    start = Signal()
    call = Signal(str, dict, object, object)  # op: str, params: dict, ret: dict (container), done: threading.Event


class Worker(BaseWorker):
    """
    Sandbox worker: executes computer-use actions via Plugin in main thread.
    It mirrors the public API of host worker. Each result includes "url".
    All Playwright operations are delegated to plugin through signals to avoid
    cross-thread greenlet violations.
    """

    WAIT_TIMEOUT = 60.0  # seconds to wait for a main-thread operation

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSandboxSignals()
        self.window = None
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

        # Viewport and pointer tracking (synced from plugin on ensure)
        self.viewport_w = 1440
        self.viewport_h = 900
        self._mouse_x = 0
        self._mouse_y = 0
        self._last_url = ""

        # Defaults
        self._default_scroll_px = 800

    # ========================= Lifecycle ========================= #

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break

                response = None
                try:
                    cmd = item.get("cmd")
                    if not cmd:
                        continue

                    # alias before gating
                    if cmd == "screenshot":
                        item = dict(item)
                        item["cmd"] = "get_screenshot"
                        cmd = "get_screenshot"

                    # allow only plugin-declared commands
                    allowed = getattr(self.plugin, "allowed_cmds", None)
                    if isinstance(allowed, (list, set, tuple)) and cmd not in allowed:
                        continue

                    response = self._dispatch(item)
                    if response:
                        responses.append(response)

                except Exception as e:
                    responses.append(self.make_response(item, self.throw_error(e)))

            if responses:
                self.reply_more(responses)

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def on_destroy(self):
        """Handle destroyed event."""
        self.cleanup()

    def cleanup(self):
        """Playwright is owned by the plugin; worker does not close it."""
        return

    # ========================= Dispatch ========================= #

    def _dispatch(self, item: dict) -> dict:
        cmd = item["cmd"]

        handler = None

        # Legacy-compatible API
        if cmd == "open_web_browser":
            handler = self.cmd_open_web_browser
        elif cmd == "get_mouse_position":
            handler = self.cmd_mouse_get_pos
        elif cmd == "mouse_move":
            handler = self.cmd_mouse_move
        elif cmd == "mouse_drag":
            handler = self.cmd_mouse_drag
        elif cmd == "mouse_click":
            handler = self.cmd_mouse_click
        elif cmd == "mouse_scroll":
            handler = self.cmd_mouse_scroll
        elif cmd == "get_screenshot":
            handler = self.cmd_make_screenshot
        elif cmd == "keyboard_key":
            handler = self.cmd_keyboard_key
        elif cmd == "keyboard_keys":
            handler = self.cmd_keyboard_keys
        elif cmd == "keyboard_type":
            handler = self.cmd_keyboard_type
        elif cmd == "wait":
            handler = self.cmd_wait

        # Google/OpenAI Computer Use
        elif cmd == "wait_5_seconds":
            handler = self.cmd_wait_5_seconds
        elif cmd == "go_back":
            handler = self.cmd_go_back
        elif cmd == "go_forward":
            handler = self.cmd_go_forward
        elif cmd == "search":
            handler = self.cmd_search
        elif cmd == "navigate":
            handler = self.cmd_navigate
        elif cmd == "click_at":
            handler = self.cmd_click_at
        elif cmd == "hover_at":
            handler = self.cmd_hover_at
        elif cmd == "type_text_at":
            handler = self.cmd_type_text_at
        elif cmd == "key_combination":
            handler = self.cmd_key_combination
        elif cmd == "scroll_document":
            handler = self.cmd_scroll_document
        elif cmd == "scroll_at":
            handler = self.cmd_scroll_at
        elif cmd == "drag_and_drop":
            handler = self.cmd_drag_and_drop

        # Action-style
        elif cmd == "click":
            handler = self.cmd_click
        elif cmd == "double_click":
            handler = self.cmd_double_click
        elif cmd == "move":
            handler = self.cmd_move
        elif cmd == "type":
            handler = self.cmd_type_text
        elif cmd == "keypress":
            handler = self.cmd_keypress
        elif cmd == "scroll":
            handler = self.cmd_scroll
        elif cmd == "drag":
            handler = self.cmd_drag

        if not handler:
            return None

        return handler(item)

    # ========================= Helpers ========================= #

    def _call(self, op: str, params: dict) -> dict:
        """
        Call plugin to perform a Playwright operation in the main thread and wait for result.
        """
        ret = {}
        done = threading.Event()
        self.signals.call.emit(op, dict(params or {}), ret, done)
        if not done.wait(self.WAIT_TIMEOUT):
            raise TimeoutError(f"Playwright op timeout: {op}")
        # update cached state if provided
        self._update_state_from_ret(ret)
        return ret

    def _update_state_from_ret(self, ret: dict):
        url = ret.get("url")
        if isinstance(url, str):
            self._last_url = url
        vw = ret.get("viewport_w")
        vh = ret.get("viewport_h")
        if isinstance(vw, int) and isinstance(vh, int) and vw > 0 and vh > 0:
            self.viewport_w, self.viewport_h = vw, vh
        mx = ret.get("mouse_x")
        my = ret.get("mouse_y")
        if isinstance(mx, int) and isinstance(my, int):
            self._mouse_x, self._mouse_y = mx, my

    def _ensure_browser(self):
        """Ensure Playwright is started in the main thread and sync viewport."""
        self.signals.start.emit()
        ret = self._call("ensure", {})
        if "viewport_w" in ret and "viewport_h" in ret:
            self.viewport_w = int(ret["viewport_w"] or self.viewport_w)
            self.viewport_h = int(ret["viewport_h"] or self.viewport_h)

    def _current_url(self) -> str:
        return self.plugin.get_last_url()
        return self._last_url or ""

    def _result_with_url(self, base: dict) -> dict:
        base = dict(base or {})
        base["url"] = self._current_url()
        return base

    def _get_screen_and_pointer(self, item: dict = None) -> dict:
        current_step = self.get_param(item, "current_step", "")
        screen_w, screen_h = self.viewport_w, self.viewport_h
        return {
            "result": "success",
            "current_step": current_step,
            "screen_w": screen_w,
            "screen_h": screen_h,
            "mouse_x": self._mouse_x,
            "mouse_y": self._mouse_y,
        }

    def _get_current(self, item: dict = None) -> dict:
        base = self._get_screen_and_pointer(item)
        return self._result_with_url(base)

    def _denorm_x(self, x_norm: int) -> int:
        x_norm = max(0, min(999, int(x_norm)))
        return int(round(x_norm / 1000.0 * self.viewport_w))

    def _denorm_y(self, y_norm: int) -> int:
        y_norm = max(0, min(999, int(y_norm)))
        return int(round(y_norm / 1000.0 * self.viewport_h))

    def _button_from_name(self, name: Optional[str]) -> str:
        if not name:
            return "left"
        name = name.lower()
        if name in ("left", "right", "middle"):
            return name
        return "left"

    def _permit(self, option_name: str) -> bool:
        try:
            if hasattr(self.plugin, "get_option_value"):
                val = self.plugin.get_option_value(option_name)
                if val is None:
                    return True
                return bool(val)
        except Exception:
            pass
        return True

    # ========================= Legacy-compatible commands ========================= #

    def cmd_open_web_browser(self, item: dict) -> dict:
        try:
            self.msg = "Open web browser (sandbox via plugin)"
            self.log(self.msg)
            self._ensure_browser()
            url = ""
            if self.has_param(item, "url"):
                url = self.get_param(item, "url") or ""
                if url:
                    self._call("navigate", {"url": url})
            result = self._get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_wait(self, item: dict) -> dict:
        wait_time = 5
        try:
            if self.has_param(item, "seconds"):
                wait_time = int(self.get_param(item, "seconds"))
            self.msg = "Wait (sandbox)"
            self.log(self.msg)
            result = self._get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        time.sleep(max(0, wait_time))
        return self.make_response(item, result)

    def cmd_mouse_get_pos(self, item: dict) -> dict:
        try:
            self.msg = "Mouse get position (sandbox)"
            self.log(self.msg)
            result = self._get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_move(self, item: dict) -> dict:
        error = None
        try:
            if not self._permit("allow_mouse_move"):
                raise RuntimeError("Mouse move not permitted by settings.")
            self._ensure_browser()
            x = int(self.get_param(item, "x", self.get_param(item, "mouse_x", 0)))
            y = int(self.get_param(item, "y", self.get_param(item, "mouse_y", 0)))
            click = self.get_param(item, "click", None)
            num = int(self.get_param(item, "num_clicks", 1))
            if click:
                # Single combined call: click at explicit coordinates
                self._call("click", {"x": x, "y": y, "button": self._button_from_name(click), "count": max(1, num)})
            else:
                self._call("move", {"x": x, "y": y})
            result = self._get_current(item)
        except Exception as e:
            error = str(e)
            result = self._get_current(item)
            result["error"] = error
            self.log("Error: {}".format(e))

        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_click(self, item: dict) -> dict:
        try:
            if not self._permit("allow_mouse_click"):
                raise RuntimeError("Mouse click not permitted by settings.")
            self._ensure_browser()
            button = self._button_from_name(self.get_param(item, "button", "left"))
            num = int(self.get_param(item, "num_clicks", 1))
            x = self.get_param(item, "x", None)
            y = self.get_param(item, "y", None)
            payload = {"button": button, "count": max(1, num)}
            if x is not None and y is not None:
                payload["x"] = int(x)
                payload["y"] = int(y)
            self._call("click", payload)
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_scroll(self, item: dict) -> dict:
        try:
            if not self._permit("allow_mouse_scroll"):
                raise RuntimeError("Mouse scroll not permitted by settings.")
            self._ensure_browser()
            x = self.get_param(item, "x", self.get_param(item, "mouse_x", None))
            y = self.get_param(item, "y", self.get_param(item, "mouse_y", None))
            dx = int(self.get_param(item, "dx", 0))
            dy = int(self.get_param(item, "dy", 0))
            unit = self.get_param(item, "unit", "px")
            if unit == "step":
                dx = int(dx) * 30
                dy = int(dy) * 30
            payload = {"dx": dx, "dy": dy}
            if x is not None and y is not None:
                payload["x"] = int(x)
                payload["y"] = int(y)
            self._call("scroll", payload)
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_drag(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            x = int(self.get_param(item, "x"))
            y = int(self.get_param(item, "y"))
            dx = int(self.get_param(item, "dx"))
            dy = int(self.get_param(item, "dy"))
            self._call("drag", {"x": x, "y": y, "dx": dx, "dy": dy})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_keyboard_keys(self, item: dict) -> dict:
        error = None
        try:
            if not self._permit("allow_keyboard"):
                raise RuntimeError("Keyboard not permitted by settings.")
            self._ensure_browser()
            keys = self.get_param(item, "keys", []) or []
            self._call("keypress_combo", {"keys": keys})
            result = self._get_current(item)
        except Exception as e:
            error = str(e)
            result = self._get_current(item)
            result["error"] = error
            self.log("Error: {}".format(e))
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_keyboard_key(self, item: dict) -> dict:
        error = None
        try:
            if not self._permit("allow_keyboard"):
                raise RuntimeError("Keyboard not permitted by settings.")
            self._ensure_browser()
            key = self.get_param(item, "key")
            modifier = self.get_param(item, "modifier", None)
            if modifier:
                self._call("keypress_combo", {"keys": [modifier, key]})
            else:
                self._call("keypress", {"key": key})
            result = self._get_current(item)
        except Exception as e:
            error = str(e)
            result = self._get_current(item)
            result["error"] = error
            self.log("Error: {}".format(e))
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_keyboard_type(self, item: dict) -> dict:
        try:
            if not self._permit("allow_keyboard"):
                raise RuntimeError("Keyboard not permitted by settings.")
            self._ensure_browser()
            text = self.get_param(item, "text", "") or ""
            modifier = self.get_param(item, "modifier", None)
            payload = {"text": text}
            if modifier:
                payload["modifier"] = modifier
            self._call("type", payload)
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_make_screenshot(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            ret = self._call("screenshot", {"full_page": False})
            img_bytes = ret.get("image", b"")
            meta = self._get_current(item)
            if img_bytes:
                self.signals.screenshot.emit(meta, img_bytes)
            result = meta
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    # ========================= Google/OpenAI Computer Use commands ========================= #

    def cmd_wait_5_seconds(self, item: dict) -> dict:
        return self.cmd_wait({"cmd": "wait", "params": {"seconds": 5}})

    def cmd_go_back(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            self._call("go_back", {})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_go_forward(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            self._call("go_forward", {})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_search(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            self._call("navigate", {"url": "https://www.google.com"})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_navigate(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            url = self.get_param(item, "url", "") or ""
            if url:
                self._call("navigate", {"url": url})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_click_at(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            x = self._denorm_x(int(self.get_param(item, "x")))
            y = self._denorm_y(int(self.get_param(item, "y")))
            # Single combined call
            self._call("click_at", {"x": x, "y": y, "button": "left", "count": 1})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_hover_at(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            x = self._denorm_x(int(self.get_param(item, "x")))
            y = self._denorm_y(int(self.get_param(item, "y")))
            # Single combined call for hover
            self._call("hover_at", {"x": x, "y": y})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_type_text_at(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            x = self._denorm_x(int(self.get_param(item, "x")))
            y = self._denorm_y(int(self.get_param(item, "y")))
            text = self.get_param(item, "text", "") or ""
            press_enter = bool(self.get_param(item, "press_enter", True))
            clear_before = bool(self.get_param(item, "clear_before_typing", True))
            # Single combined call for full flow
            self._call("type_text_at", {
                "x": x,
                "y": y,
                "text": text,
                "press_enter": press_enter,
                "clear_before_typing": clear_before,
            })
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_key_combination(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            keys = self.get_param(item, "keys", None)
            if isinstance(keys, str):
                parts = [p.strip() for p in keys.replace("+", " ").split() if p.strip()]
            else:
                parts = list(keys or [])
            self._call("keypress_combo", {"keys": parts})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_scroll_document(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            direction = str(self.get_param(item, "direction", "down")).lower()
            magnitude = int(self.get_param(item, "magnitude", self._default_scroll_px))
            dx, dy = 0, 0
            if direction == "down":
                dy = magnitude
            elif direction == "up":
                dy = -magnitude
            elif direction == "left":
                dx = -magnitude
            elif direction == "right":
                dx = magnitude
            self._call("scroll", {"dx": dx, "dy": dy})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_scroll_at(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            direction = str(self.get_param(item, "direction", "down")).lower()
            magnitude = int(self.get_param(item, "magnitude", self._default_scroll_px))
            x = self._denorm_x(int(self.get_param(item, "x"))) if self.has_param(item, "x") else None
            y = self._denorm_y(int(self.get_param(item, "y"))) if self.has_param(item, "y") else None
            dx, dy = 0, 0
            if direction == "down":
                dy = magnitude
            elif direction == "up":
                dy = -magnitude
            elif direction == "left":
                dx = -magnitude
            elif direction == "right":
                dx = magnitude
            payload = {"dx": dx, "dy": dy}
            if x is not None and y is not None:
                payload["x"] = x
                payload["y"] = y
            self._call("scroll", payload)
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_drag_and_drop(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            x0 = self._denorm_x(int(self.get_param(item, "x")))
            y0 = self._denorm_y(int(self.get_param(item, "y")))
            x1 = self._denorm_x(int(self.get_param(item, "destination_x")))
            y1 = self._denorm_y(int(self.get_param(item, "destination_y")))
            self._call("drag", {"x": x0, "y": y0, "dx": x1, "dy": y1})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    # ========================= Action-style convenience ========================= #

    def cmd_click(self, item: dict) -> dict:
        item2 = dict(item)
        if self.has_param(item, "x") and self.has_param(item, "y"):
            x = int(self.get_param(item, "x")); y = int(self.get_param(item, "y"))
            if 0 <= x <= 999 and 0 <= y <= 999:
                item2["params"] = dict(item.get("params", {}))
                item2["params"]["x"] = self._denorm_x(x)
                item2["params"]["y"] = self._denorm_y(y)
        return self.cmd_mouse_click(item2)

    def cmd_double_click(self, item: dict) -> dict:
        item2 = dict(item)
        p = dict(item.get("params", {}))
        p["num_clicks"] = 2
        item2["params"] = p
        return self.cmd_click(item2)

    def cmd_move(self, item: dict) -> dict:
        item2 = dict(item)
        p = dict(item.get("params", {}))
        if "x" in p and "y" in p:
            x = int(p["x"]); y = int(p["y"])
            if 0 <= x <= 999 and 0 <= y <= 999:
                p["x"] = self._denorm_x(x); p["y"] = self._denorm_y(y)
        item2["params"] = p
        item2["cmd"] = "mouse_move"
        return self.cmd_mouse_move(item2)

    def cmd_type_text(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "keyboard_type"
        return self.cmd_keyboard_type(item2)

    def cmd_keypress(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            keys = self.get_param(item, "keys", []) or []
            for k in keys:
                self._call("keypress", {"key": k})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_scroll(self, item: dict) -> dict:
        item2 = dict(item)
        p = dict(item.get("params", {}))
        x = p.get("x", None); y = p.get("y", None)
        if x is not None and y is not None:
            if 0 <= int(x) <= 999 and 0 <= int(y) <= 999:
                p["x"] = self._denorm_x(int(x)); p["y"] = self._denorm_y(int(y))
        dx = int(p.get("scroll_x", p.get("dx", 0))); dy = int(p.get("scroll_y", p.get("dy", 0)))
        p["dx"], p["dy"] = dx, dy
        p["unit"] = "px"
        item2["params"] = p
        item2["cmd"] = "mouse_scroll"
        return self.cmd_mouse_scroll(item2)

    def cmd_drag(self, item: dict) -> dict:
        try:
            self._ensure_browser()
            path = self.get_param(item, "path", [])
            if not path or len(path) < 2:
                x = self.get_param(item, "x", None)
                y = self.get_param(item, "y", None)
                dx = self.get_param(item, "dx", None)
                dy = self.get_param(item, "dy", None)
                if None in (x, y, dx, dy):
                    return self.make_response(item, self._get_current(item))
                pts = [{"x": x, "y": y}, {"x": dx, "y": dy}]
            else:
                pts = path

            def den(p):
                xx = int(p["x"]); yy = int(p["y"])
                if 0 <= xx <= 999 and 0 <= yy <= 999:
                    return self._denorm_x(xx), self._denorm_y(yy)
                return xx, yy

            x0, y0 = den(pts[0]); x1, y1 = den(pts[1])
            self._call("drag", {"x": x0, "y": y0, "dx": x1, "dy": y1})
            result = self._get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)