#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import os
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional

import mss

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    screenshot = Signal(dict, object)


class Worker(BaseWorker):
    """
    Host worker: executes computer-use actions using native OS input.
    It supports the full set of Computer Use commands. Each response includes "url" (empty on host).
    """

    _uinput_keyboard = None
    _uinput_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.window = None
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    @Slot()
    def run(self):
        try:
            responses = []
            stop_on_error = bool(getattr(self.ctx, "extra", {}).get("computer_stop_on_error", False))
            batch_failed = False
            for item in self.cmds:
                if self.is_stopped():
                    break
                if stop_on_error and batch_failed:
                    responses.append(self.make_response(item, {
                        "result": "error",
                        "error": "Not executed: an earlier computer action in this turn failed.",
                        "not_executed": True,
                        "no_screenshot": True,
                    }))
                    continue
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
                        responses.append(self.make_response(item, {
                            "result": "error",
                            "error": f"Computer Use action '{cmd}' is not implemented by PyGPT.",
                        }))
                        if stop_on_error:
                            batch_failed = True
                        continue

                    permission_error = self._permission_error(cmd)
                    if permission_error:
                        response = self.make_response(item, {"result": "error", "error": permission_error})
                    # open web browser
                    elif cmd == "open_web_browser":
                        response = self.cmd_open_web_browser(item)

                    # get mouse position
                    elif cmd == "get_mouse_position":
                        response = self.cmd_mouse_get_pos(item)

                    # set mouse position
                    elif cmd == "mouse_move":
                        if self.plugin.get_option_value("allow_mouse_move"):
                            response = self.cmd_mouse_move(item)

                    # drag mouse
                    elif cmd == "mouse_drag":
                        if self.plugin.get_option_value("allow_mouse_move"):
                            response = self.cmd_mouse_drag(item)

                    # mouse click
                    elif cmd == "mouse_click":
                        if self.plugin.get_option_value("allow_mouse_click"):
                            response = self.cmd_mouse_click(item)

                    # mouse scroll
                    elif cmd == "mouse_scroll":
                        if self.plugin.get_option_value("allow_mouse_scroll"):
                            response = self.cmd_mouse_scroll(item)

                    # screenshot
                    elif cmd == "get_screenshot":
                        if self.plugin.get_option_value("allow_screenshot"):
                            response = self.cmd_make_screenshot(item)

                    # keyboard key
                    elif cmd == "keyboard_key":
                        if self.plugin.get_option_value("allow_keyboard"):
                            response = self.cmd_keyboard_key(item)

                    # keyboard keys
                    elif cmd == "keyboard_keys":
                        if self.plugin.get_option_value("allow_keyboard"):
                            response = self.cmd_keyboard_keys(item)

                    # keyboard type
                    elif cmd == "keyboard_type":
                        if self.plugin.get_option_value("allow_keyboard"):
                            response = self.cmd_keyboard_type(item)

                    # wait
                    elif cmd == "wait":
                        response = self.cmd_wait(item)

                    # Computer Use: added commands (host-native)
                    elif cmd == "wait_5_seconds":
                        response = self.cmd_wait_5_seconds(item)
                    elif cmd == "go_back":
                        response = self.cmd_go_back(item)
                    elif cmd == "go_forward":
                        response = self.cmd_go_forward(item)
                    elif cmd == "search":
                        response = self.cmd_search(item)
                    elif cmd == "navigate":
                        response = self.cmd_navigate(item)
                    elif cmd == "click_at":
                        response = self.cmd_click_at(item)
                    elif cmd == "hover_at":
                        response = self.cmd_hover_at(item)
                    elif cmd == "type_text_at":
                        response = self.cmd_type_text_at(item)
                    elif cmd == "key_combination":
                        response = self.cmd_key_combination(item)
                    elif cmd == "scroll_document":
                        response = self.cmd_scroll_document(item)
                    elif cmd == "scroll_at":
                        response = self.cmd_scroll_at(item)
                    elif cmd == "drag_and_drop":
                        response = self.cmd_drag_and_drop(item)

                    # Action-style
                    elif cmd == "click":
                        response = self.cmd_click(item)
                    elif cmd == "double_click":
                        response = self.cmd_double_click(item)
                    elif cmd == "move":
                        response = self.cmd_move(item)
                    elif cmd == "type":
                        response = self.cmd_type_text(item)
                    elif cmd == "keypress":
                        response = self.cmd_keypress(item)
                    elif cmd == "scroll":
                        response = self.cmd_scroll(item)
                    elif cmd == "drag":
                        response = self.cmd_drag(item)
                    elif cmd == "mouse_down":
                        response = self.cmd_mouse_down(item)
                    elif cmd == "mouse_up":
                        response = self.cmd_mouse_up(item)
                    elif cmd == "key_down":
                        response = self.cmd_key_down(item)
                    elif cmd == "key_up":
                        response = self.cmd_key_up(item)
                    elif cmd == "hold_key":
                        response = self.cmd_hold_key(item)
                    elif cmd == "long_press":
                        response = self.cmd_long_press(item)
                    elif cmd == "press_key":
                        response = self.cmd_keyboard_key({"cmd": "keyboard_key", "params": {"key": self.get_param(item, "key")}})
                    elif cmd == "hotkey":
                        response = self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": {"keys": self.get_param(item, "keys", [])}})
                    elif cmd == "take_screenshot":
                        response = self.cmd_make_screenshot(item)
                    elif cmd in {"triple_click", "middle_click", "right_click"}:
                        p = dict(item.get("params", {}))
                        if cmd == "triple_click":
                            p["num_clicks"] = 3
                        elif cmd == "middle_click":
                            p["button"] = "middle"
                        else:
                            p["button"] = "right"
                        response = self.cmd_mouse_click({"cmd": "mouse_click", "params": p})
                    elif cmd == "computer_unimplemented":
                        provider = str(self.get_param(item, "provider", "provider") or "provider")
                        action = str(self.get_param(item, "action", "unknown") or "unknown")
                        details = str(self.get_param(item, "details", "") or "").strip()
                        message = (
                            f"Computer Use action '{action}' from {provider} is not implemented by PyGPT."
                        )
                        if details:
                            message += f" {details}"
                        response = self.make_response(item, {
                            "result": "error",
                            "error": message,
                        })

                    # Never silently consume a provider command that reached this
                    # worker but has no implementation in the current build.
                    if response is None:
                        response = self.make_response(item, {
                            "result": "error",
                            "error": f"Computer Use action '{cmd}' is not implemented by PyGPT.",
                        })

                    if response:
                        responses.append(response)
                        if stop_on_error and self._response_has_error(response):
                            batch_failed = True

                except Exception as e:
                    error_response = self.make_response(item, self.throw_error(e))
                    responses.append(error_response)
                    if stop_on_error:
                        batch_failed = True

            if len(responses) > 0:
                self.reply_more(responses)  # send response

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def on_destroy(self):
        """Handle destroyed event."""
        self.cleanup()

    # ========================= Helpers ========================= #

    def _permission_error(self, cmd: str) -> Optional[str]:
        groups = {
            "allow_mouse_move": {"mouse_move", "mouse_drag", "move", "drag", "drag_and_drop", "hover_at"},
            "allow_mouse_click": {"mouse_click", "click", "double_click", "triple_click", "middle_click",
                                  "right_click", "click_at", "mouse_down", "mouse_up", "long_press"},
            "allow_mouse_scroll": {"mouse_scroll", "scroll", "scroll_at", "scroll_document"},
            "allow_screenshot": {"get_screenshot", "take_screenshot", "screenshot"},
            "allow_keyboard": {"keyboard_key", "keyboard_keys", "keyboard_type", "keypress", "press_key",
                               "hotkey", "key_combination", "key_down", "key_up", "hold_key", "type", "type_text_at"},
        }
        for option, commands in groups.items():
            if cmd in commands and not bool(self.plugin.get_option_value(option)):
                return f"Computer Use action '{cmd}' is not permitted by plugin settings."
        return None

    @staticmethod
    def _response_has_error(response: dict) -> bool:
        if not isinstance(response, dict):
            return False
        result = response.get("result")
        if isinstance(result, dict):
            if result.get("error"):
                return True
            status = str(result.get("result", "")).lower()
            return status in {"error", "failed", "failure"}
        return isinstance(result, str) and result.lower().startswith("error")

    def _get_screen_size(self) -> tuple:
        """Return the pixel size of the same monitor used by Computer Use screenshots."""
        _, _, width, height = self._get_screen_geometry()
        return width, height

    def _denorm_x(self, x_norm: int) -> int:
        left, _, width, _ = self._get_screen_geometry()
        x_norm = max(0, min(999, int(x_norm)))
        return left + min(width - 1, int(round(x_norm / 1000.0 * width)))

    def _denorm_y(self, y_norm: int) -> int:
        _, top, _, height = self._get_screen_geometry()
        y_norm = max(0, min(999, int(y_norm)))
        return top + min(height - 1, int(round(y_norm / 1000.0 * height)))

    def _get_screen_geometry(self) -> tuple:
        """Return (left, top, width, height) for the monitor captured by MSS."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                return (
                    int(monitor.get("left", 0)),
                    int(monitor.get("top", 0)),
                    int(monitor.get("width", 0)),
                    int(monitor.get("height", 0)),
                )
        except Exception:
            screen = self.window.app.primaryScreen()
            geometry = screen.geometry()
            return geometry.x(), geometry.y(), geometry.width(), geometry.height()

    def _coordinate_space(self, item: dict) -> str:
        space = str(self.get_param(item, "coordinate_space", "global") or "global").lower().strip()
        if space in {"normalized", "normalized_1000", "google"}:
            return "normalized"
        if space in {"screen", "screen_px", "screenshot", "pixel", "pixels"}:
            return "screen"
        return "global"

    def _to_screen_point(self, item: dict, x, y) -> tuple:
        """Convert provider coordinates to native global screen coordinates."""
        xi, yi = int(x), int(y)
        space = self._coordinate_space(item)
        if space == "normalized":
            return self._denorm_x(xi), self._denorm_y(yi)
        if space == "screen":
            left, top, width, height = self._get_screen_geometry()
            xi = max(0, min(max(0, width - 1), xi))
            yi = max(0, min(max(0, height - 1), yi))
            return left + xi, top + yi
        return xi, yi

    def _normalize_drag_path(self, item: dict, path) -> list:
        points = []
        for point in path or []:
            try:
                if isinstance(point, dict):
                    x, y = point.get("x"), point.get("y")
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    x, y = point[0], point[1]
                else:
                    continue
                points.append(self._to_screen_point(item, x, y))
            except Exception:
                continue
        return points

    def _parse_keys(self, value) -> list:
        if isinstance(value, str):
            return [p.strip() for p in value.replace("+", " ").split() if p.strip()]
        out = []
        for key in value or []:
            if isinstance(key, str) and "+" in key:
                out.extend([p.strip() for p in key.split("+") if p.strip()])
            else:
                out.append(key)
        return out

    @staticmethod
    def _linux_session_type() -> str:
        return str(os.environ.get("XDG_SESSION_TYPE", "") or "").strip().lower()

    @staticmethod
    def _key_name(key) -> str:
        if isinstance(key, str):
            return key.strip()
        name = getattr(key, "name", None)
        return str(name if name is not None else key).strip()

    def _x11_keysym_name(self, key) -> str:
        """Map a Computer Use key name to an X11 keysym name."""
        raw = self._key_name(key)
        upper = raw.upper()
        mapping = {
            "CTRL": "Control_L",
            "CONTROL": "Control_L",
            "CTRL_L": "Control_L",
            "CONTROL_L": "Control_L",
            "CTRL_R": "Control_R",
            "CONTROL_R": "Control_R",
            "ALT": "Alt_L",
            "ALT_L": "Alt_L",
            "ALT_R": "Alt_R",
            "ALTGR": "ISO_Level3_Shift",
            "ALT_GR": "ISO_Level3_Shift",
            "SHIFT": "Shift_L",
            "SHIFT_L": "Shift_L",
            "SHIFT_R": "Shift_R",
            "CMD": "Super_L",
            "COMMAND": "Super_L",
            "SUPER": "Super_L",
            "START": "Super_L",
            "WIN": "Super_L",
            "WINDOWS": "Super_L",
            "META": "Super_L",
            "ENTER": "Return",
            "RETURN": "Return",
            "ESC": "Escape",
            "ESCAPE": "Escape",
            "BACKSPACE": "BackSpace",
            "TAB": "Tab",
            "SPACE": "space",
            "LEFT": "Left",
            "RIGHT": "Right",
            "UP": "Up",
            "DOWN": "Down",
            "PAGEUP": "Page_Up",
            "PAGE_UP": "Page_Up",
            "PAGEDOWN": "Page_Down",
            "PAGE_DOWN": "Page_Down",
            "HOME": "Home",
            "END": "End",
            "DELETE": "Delete",
            "DEL": "Delete",
            "INSERT": "Insert",
            "INS": "Insert",
            "PRINTSCREEN": "Print",
            "PRINT_SCREEN": "Print",
            "PRTSC": "Print",
        }
        if upper in mapping:
            return mapping[upper]
        if upper.startswith("F") and upper[1:].isdigit():
            return upper
        # keyboard_keys/keypress represents a physical shortcut key, not text.
        # Do not infer Shift from an uppercase letter such as "T" in CTRL+ALT+T.
        if len(raw) == 1 and raw.isalpha():
            return raw.lower()
        return raw

    def _try_x11_xtest_chord(self, keys, hold: float, key_delay: float) -> bool:
        """
        Emit the complete chord through XTEST.

        pynput's Xorg backend uses XTEST for special keys but may use XSendEvent
        for printable characters.  The latter reaches the focused X window but
        is not seen by many desktop-environment global shortcut handlers.  This
        is why a sequence such as CTRL+ALT+T can report success while the
        terminal never opens.  Sending *all* members of the chord through XTEST
        makes the key sequence indistinguishable from normal X11 input for the
        global shortcut manager.
        """
        if not sys.platform.startswith("linux") or not os.environ.get("DISPLAY"):
            return False

        try:
            from Xlib import X, XK, display
            from Xlib.ext import xtest
        except Exception:
            return False

        dpy = None
        pressed = []
        try:
            dpy = display.Display()
            keycodes = []
            for key in self._parse_keys(keys):
                name = self._x11_keysym_name(key)
                keysym = XK.string_to_keysym(name)
                if not keysym and len(name) == 1:
                    keysym = ord(name)
                if not keysym:
                    return False
                keycode = int(dpy.keysym_to_keycode(keysym) or 0)
                if keycode <= 0:
                    return False
                keycodes.append(keycode)

            if not keycodes:
                return False

            for keycode in keycodes:
                xtest.fake_input(dpy, X.KeyPress, keycode)
                dpy.sync()
                pressed.append(keycode)
                if key_delay > 0:
                    time.sleep(key_delay)

            if hold > 0:
                time.sleep(hold)

            for keycode in reversed(pressed):
                xtest.fake_input(dpy, X.KeyRelease, keycode)
                dpy.sync()
                if key_delay > 0:
                    time.sleep(key_delay)
            pressed.clear()
            return True
        except Exception as e:
            self.log("XTEST keyboard fallback failed: {}".format(e))
            return False
        finally:
            if dpy is not None:
                # Never leave modifiers down after a partial failure.
                for keycode in reversed(pressed):
                    try:
                        xtest.fake_input(dpy, X.KeyRelease, keycode)
                    except Exception:
                        pass
                try:
                    dpy.sync()
                    dpy.close()
                except Exception:
                    pass

    @staticmethod
    def _linux_evdev_keycode(key) -> Optional[int]:
        """Resolve common Computer Use shortcut keys to Linux input keycodes."""
        raw = str(key or "").strip()
        upper = raw.upper()
        special = {
            "ESC": 1, "ESCAPE": 1,
            "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
            "MINUS": 12, "-": 12, "EQUAL": 13, "=": 13,
            "BACKSPACE": 14, "TAB": 15,
            "Q": 16, "W": 17, "E": 18, "R": 19, "T": 20, "Y": 21, "U": 22, "I": 23, "O": 24, "P": 25,
            "LEFTBRACE": 26, "[": 26, "RIGHTBRACE": 27, "]": 27, "ENTER": 28, "RETURN": 28,
            "CTRL": 29, "CONTROL": 29, "CTRL_L": 29, "CONTROL_L": 29,
            "A": 30, "S": 31, "D": 32, "F": 33, "G": 34, "H": 35, "J": 36, "K": 37, "L": 38,
            "SEMICOLON": 39, ";": 39, "APOSTROPHE": 40, "'": 40, "GRAVE": 41, "`": 41,
            "SHIFT": 42, "SHIFT_L": 42, "BACKSLASH": 43, "\\": 43,
            "Z": 44, "X": 45, "C": 46, "V": 47, "B": 48, "N": 49, "M": 50,
            "COMMA": 51, ",": 51, "DOT": 52, ".": 52, "SLASH": 53, "/": 53,
            "SHIFT_R": 54, "ALT": 56, "ALT_L": 56, "SPACE": 57,
            "F1": 59, "F2": 60, "F3": 61, "F4": 62, "F5": 63, "F6": 64, "F7": 65, "F8": 66, "F9": 67, "F10": 68,
            "HOME": 102, "UP": 103, "PAGEUP": 104, "PAGE_UP": 104, "LEFT": 105, "RIGHT": 106,
            "END": 107, "DOWN": 108, "PAGEDOWN": 109, "PAGE_DOWN": 109, "INSERT": 110, "DELETE": 111,
            "F11": 87, "F12": 88, "CTRL_R": 97, "CONTROL_R": 97, "ALT_R": 100, "ALTGR": 100, "ALT_GR": 100,
            "SUPER": 125, "CMD": 125, "COMMAND": 125, "START": 125, "WIN": 125, "WINDOWS": 125, "META": 125,
        }
        return special.get(upper)

    def _try_evdev_uinput_chord(self, keys, hold: float, key_delay: float) -> bool:
        """Inject a real Linux virtual keyboard through /dev/uinput when permitted."""
        try:
            from evdev import UInput, ecodes
        except Exception:
            return False

        codes = []
        for key in self._parse_keys(keys):
            code = self._linux_evdev_keycode(self._key_name(key))
            if code is None:
                return False
            codes.append(code)
        if not codes:
            return False

        try:
            with self.__class__._uinput_lock:
                ui = self.__class__._uinput_keyboard
                if ui is None:
                    supported = sorted(set(
                        code for code in (self._linux_evdev_keycode(name) for name in [
                            "ESC", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=",
                            "BACKSPACE", "TAB", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P",
                            "[", "]", "ENTER", "CTRL", "A", "S", "D", "F", "G", "H", "J", "K", "L",
                            ";", "'", "`", "SHIFT", "\\", "Z", "X", "C", "V", "B", "N", "M",
                            ",", ".", "/", "SHIFT_R", "ALT", "SPACE", "F1", "F2", "F3", "F4", "F5",
                            "F6", "F7", "F8", "F9", "F10", "F11", "F12", "HOME", "UP", "PAGEUP",
                            "LEFT", "RIGHT", "END", "DOWN", "PAGEDOWN", "INSERT", "DELETE", "CTRL_R",
                            "ALT_R", "SUPER",
                        ]) if code is not None
                    ))
                    ui = UInput({ecodes.EV_KEY: supported}, name="PyGPT Computer Use Keyboard")
                    self.__class__._uinput_keyboard = ui
                    # Give the compositor/udev a moment to register the persistent virtual device.
                    time.sleep(0.12)

                pressed = []
                try:
                    for code in codes:
                        ui.write(ecodes.EV_KEY, code, 1)
                        ui.syn()
                        pressed.append(code)
                        if key_delay > 0:
                            time.sleep(key_delay)
                    if hold > 0:
                        time.sleep(hold)
                finally:
                    for code in reversed(pressed):
                        try:
                            ui.write(ecodes.EV_KEY, code, 0)
                            ui.syn()
                        except Exception:
                            pass
                        if key_delay > 0:
                            time.sleep(key_delay)
            return True
        except Exception as e:
            self.log("uinput keyboard fallback failed: {}".format(e))
            return False

    def _try_ydotool_chord(self, keys, key_delay: float) -> bool:
        """Use kernel uinput through ydotool/ydotoold when available (Wayland-safe)."""
        binary = shutil.which("ydotool")
        if not binary:
            return False
        codes = []
        for key in self._parse_keys(keys):
            code = self._linux_evdev_keycode(self._key_name(key))
            if code is None:
                return False
            codes.append(code)
        if not codes:
            return False
        delay_ms = max(1, min(1000, int(round(key_delay * 1000.0))))
        events = [f"{code}:1" for code in codes] + [f"{code}:0" for code in reversed(codes)]
        try:
            proc = subprocess.run(
                [binary, "key", "-d", str(delay_ms), *events],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0:
                return True
            self.log("ydotool keyboard fallback failed: {}".format((proc.stderr or proc.stdout or "").strip()))
        except Exception as e:
            self.log("ydotool keyboard fallback failed: {}".format(e))
        return False

    def _try_wtype_chord(self, keys, hold: float) -> bool:
        """Use Wayland virtual-keyboard protocol through wtype when installed."""
        binary = shutil.which("wtype")
        if not binary:
            return False
        modifiers = {
            "CTRL": "ctrl", "CONTROL": "ctrl", "CTRL_L": "ctrl", "CONTROL_L": "ctrl",
            "ALT": "alt", "ALT_L": "alt", "SHIFT": "shift", "SHIFT_L": "shift",
            "SUPER": "logo", "CMD": "logo", "COMMAND": "logo", "START": "logo",
            "WIN": "logo", "WINDOWS": "logo", "META": "logo",
            "ALTGR": "altgr", "ALT_GR": "altgr",
        }
        named = {
            "ENTER": "Return", "RETURN": "Return", "ESC": "Escape", "ESCAPE": "Escape",
            "BACKSPACE": "BackSpace", "TAB": "Tab", "SPACE": "space",
            "LEFT": "Left", "RIGHT": "Right", "UP": "Up", "DOWN": "Down",
            "PAGEUP": "Page_Up", "PAGE_UP": "Page_Up", "PAGEDOWN": "Page_Down", "PAGE_DOWN": "Page_Down",
            "HOME": "Home", "END": "End", "DELETE": "Delete", "INSERT": "Insert",
        }
        args = [binary]
        active_modifiers = []
        regular = []
        for key in self._parse_keys(keys):
            raw = self._key_name(key)
            upper = raw.upper()
            if upper in modifiers:
                mod = modifiers[upper]
                if mod not in active_modifiers:
                    active_modifiers.append(mod)
                    args.extend(["-M", mod])
            else:
                name = named.get(upper, upper if upper.startswith("F") and upper[1:].isdigit() else raw.lower() if len(raw) == 1 and raw.isalpha() else raw)
                regular.append(name)
                args.extend(["-P", name])
        if not active_modifiers and not regular:
            return False
        if hold > 0:
            args.extend(["-s", str(max(1, min(1000, int(round(hold * 1000.0)))))])
        for name in reversed(regular):
            args.extend(["-p", name])
        for mod in reversed(active_modifiers):
            args.extend(["-m", mod])
        try:
            proc = subprocess.run(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, check=False
            )
            if proc.returncode == 0:
                return True
            self.log("wtype keyboard fallback failed: {}".format((proc.stderr or proc.stdout or "").strip()))
        except Exception as e:
            self.log("wtype keyboard fallback failed: {}".format(e))
        return False

    def _send_key_chord(self, keys, hold: float = 0.04, key_delay: float = 0.012) -> tuple:
        """Send a key chord and return (backend, warning)."""
        parsed = self._parse_keys(keys)
        if not parsed:
            raise ValueError("keyboard_keys requires at least one key")

        hold = max(0.0, min(1.0, float(hold or 0.0)))
        key_delay = max(0.0, min(0.25, float(key_delay or 0.0)))
        warning = None

        if sys.platform.startswith("linux"):
            session = self._linux_session_type()
            # Wayland/XWayland does not guarantee that pynput/XTEST events reach
            # the compositor. Prefer real virtual-keyboard/uinput backends.
            if session == "wayland":
                if self._try_ydotool_chord(parsed, key_delay):
                    return "ydotool-uinput", None
                if self._try_evdev_uinput_chord(parsed, hold, key_delay):
                    return "evdev-uinput", None
                if self._try_wtype_chord(parsed, hold):
                    return "wtype-wayland", None

            # XTEST is the reliable X11 path and, unlike pynput's printable-key
            # fallback, is visible to desktop global shortcut handlers.
            if self._try_x11_xtest_chord(parsed, hold, key_delay):
                if session == "wayland":
                    warning = (
                        "Keyboard chord was injected through XWayland/XTEST because no native Wayland "
                        "input backend was available; compositor-global shortcuts may ignore it."
                    )
                return "x11-xtest", warning

        keyboard = KeyboardController()
        pressed = []
        try:
            for key in parsed:
                mapped = self.remap_key(key)
                keyboard.press(mapped)
                pressed.append(mapped)
                if key_delay > 0:
                    time.sleep(key_delay)
            if hold > 0:
                time.sleep(hold)
        finally:
            for key in reversed(pressed):
                try:
                    keyboard.release(key)
                except Exception:
                    pass
                if key_delay > 0:
                    time.sleep(key_delay)

        if sys.platform.startswith("linux") and self._linux_session_type() == "wayland":
            warning = (
                "pynput is running through the Linux fallback on Wayland; global compositor shortcuts "
                "may not receive synthetic keys. Install/run ydotoold or wtype for native Wayland injection."
            )
        return "pynput", warning

    def _press_keys_down(self, keyboard, keys) -> list:
        pressed = []
        for key in self._parse_keys(keys):
            mapped = self.remap_key(key)
            keyboard.press(mapped)
            pressed.append(mapped)
        return pressed

    @staticmethod
    def _release_keys(keyboard, pressed) -> None:
        for key in reversed(pressed or []):
            try:
                keyboard.release(key)
            except Exception:
                pass

    def _with_mouse_modifiers(self, item: dict, callback):
        keys = self.get_param(item, "keys", []) or []
        if not keys:
            return callback()
        keyboard = KeyboardController()
        pressed = []
        try:
            pressed = self._press_keys_down(keyboard, keys)
            return callback()
        finally:
            self._release_keys(keyboard, pressed)

    def _is_mac(self) -> bool:
        return sys.platform == "darwin"

    # ========================= Legacy-compatible commands ========================= #

    def cmd_open_web_browser(self, item: dict) -> dict:
        """
        Open web browser

        :param item: command item
        :return: response item
        """
        import webbrowser

        try:
            self.msg = "Open web browser"
            self.log(self.msg)
            url = ""
            if self.has_param(item, "url"):
                url = self.get_param(item, "url")
            webbrowser.open(url)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_wait(self, item: dict) -> dict:
        """
        Wait

        :param item: command item
        :return: response item
        """
        wait_time = 5
        try:
            if self.has_param(item, "seconds"):
                wait_time = int(self.get_param(item, "seconds"))
            self.msg = "Wait"
            self.log(self.msg)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        time.sleep(wait_time)
        return self.make_response(item, result)

    def cmd_mouse_get_pos(self, item: dict) -> dict:
        """
        Get mouse position

        :param item: command item
        :return: response item
        """
        try:
            self.msg = "Mouse get position"
            self.log(self.msg)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_mouse_move(self, item: dict) -> dict:
        """Move the mouse in an explicit coordinate space and optionally click."""
        error = None
        click = self.get_param(item, "click", None)
        num_clicks = int(self.get_param(item, "num_clicks", 1) or 1)
        x = self.get_param(item, "x", self.get_param(item, "mouse_x", 0))
        y = self.get_param(item, "y", self.get_param(item, "mouse_y", 0))
        try:
            px, py = self._to_screen_point(item, x, y)
            mouse = MouseController()
            mouse.position = (px, py)
            if click:
                time.sleep(0.03)
                nested = {
                    "cmd": "mouse_click",
                    "params": {
                        "button": click,
                        "num_clicks": num_clicks,
                        "x": px,
                        "y": py,
                        "coordinate_space": "global",
                        "keys": self.get_param(item, "keys", []),
                    }
                }
                self.cmd_mouse_click(nested)
        except Exception as e:
            error = str(e)
            self.log("Error: {}".format(e))
        try:
            result = self.get_current(item)
            if error:
                result["error"] = error
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_click(self, item: dict) -> dict:
        """Click at an optional point, honoring modifiers and click count."""
        button = Button.left
        btn_name = str(self.get_param(item, "button", "left") or "left").lower()
        if btn_name == "middle":
            button = Button.middle
        elif btn_name == "right":
            button = Button.right
        num = max(1, int(self.get_param(item, "num_clicks", 1) or 1))
        x = self.get_param(item, "x", None)
        y = self.get_param(item, "y", None)
        try:
            mouse = MouseController()
            if x is not None and y is not None:
                px, py = self._to_screen_point(item, x, y)
                mouse.position = (px, py)
                time.sleep(0.03)
            self._with_mouse_modifiers(item, lambda: mouse.click(button, num))
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_scroll(self, item: dict) -> dict:
        """Scroll at an optional point. viewport mode follows browser wheel signs (positive Y = down)."""
        x = self.get_param(item, "x", self.get_param(item, "mouse_x", None))
        y = self.get_param(item, "y", self.get_param(item, "mouse_y", None))
        dx = int(self.get_param(item, "dx", 0) or 0)
        dy = int(self.get_param(item, "dy", 0) or 0)
        unit = str(self.get_param(item, "unit", "step") or "step").lower()
        scroll_mode = str(self.get_param(item, "scroll_mode", "native") or "native").lower()
        conversion_factor = max(1, int(self.get_param(item, "pixels_per_step", 30) or 30))
        delay = 0.01
        try:
            mouse = MouseController()
            if x is not None and y is not None:
                px, py = self._to_screen_point(item, x, y)
                mouse.position = (px, py)
                time.sleep(0.03)

            if unit == "px":
                notches_x = int(round(dx / conversion_factor)) if dx else 0
                notches_y = int(round(dy / conversion_factor)) if dy else 0
                if dx and notches_x == 0:
                    notches_x = 1 if dx > 0 else -1
                if dy and notches_y == 0:
                    notches_y = 1 if dy > 0 else -1
            else:
                notches_x, notches_y = dx, dy

            # Playwright/OpenAI/Gemini use positive vertical delta for scrolling down;
            # pynput uses positive Y for scrolling up.
            if scroll_mode in {"viewport", "browser", "screen_delta"}:
                notches_y = -notches_y

            def do_scroll():
                for _ in range(abs(notches_x)):
                    mouse.scroll(1 if notches_x > 0 else -1, 0)
                    time.sleep(delay)
                for _ in range(abs(notches_y)):
                    mouse.scroll(0, 1 if notches_y > 0 else -1)
                    time.sleep(delay)

            self._with_mouse_modifiers(item, do_scroll)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_mouse_drag(self, item: dict) -> dict:
        """Drag along the complete provider path; interpolate a two-point drag for smoothness."""
        try:
            path = self.get_param(item, "path", None)
            points = self._normalize_drag_path(item, path) if path else []
            if len(points) < 2:
                x = self.get_param(item, "x", self.get_param(item, "mouse_x", None))
                y = self.get_param(item, "y", self.get_param(item, "mouse_y", None))
                dx = self.get_param(item, "dx", None)
                dy = self.get_param(item, "dy", None)
                if None in (x, y, dx, dy):
                    raise ValueError("mouse_drag requires path with at least two points or x/y/dx/dy")
                points = [self._to_screen_point(item, x, y), self._to_screen_point(item, dx, dy)]

            if len(points) == 2:
                (x0, y0), (x1, y1) = points
                steps = max(2, int(self.get_param(item, "steps", 12) or 12))
                points = [
                    (round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps))
                    for i in range(steps + 1)
                ]

            mouse = MouseController()
            mouse.position = points[0]
            time.sleep(0.03)

            def do_drag():
                mouse.press(Button.left)
                try:
                    for point in points[1:]:
                        mouse.position = point
                        time.sleep(0.01)
                finally:
                    mouse.release(Button.left)

            self._with_mouse_modifiers(item, do_drag)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_keyboard_keys(self, item: dict) -> dict:
        """Press a true key chord through the most reliable platform backend."""
        error = None
        backend = None
        warning = None
        keys = self._parse_keys(self.get_param(item, "keys", []) or [])
        if self.plugin.get_option_value("auto_focus"):
            self.set_focus()
            time.sleep(0.15)
        repeat = max(1, int(self.get_param(item, "repeat", 1) or 1))
        hold = float(self.get_param(item, "hold", 0.04) or 0.04)
        key_delay = float(self.get_param(item, "key_delay", 0.012) or 0.012)
        try:
            for _ in range(repeat):
                backend, warning = self._send_key_chord(keys, hold=hold, key_delay=key_delay)
                if repeat > 1:
                    time.sleep(max(0.02, key_delay))
        except Exception as e:
            error = str(e)
            self.log("Error: {}".format(e))
        try:
            result = self.get_current(item)
            if backend:
                result["input_backend"] = backend
            if warning:
                result["warning"] = warning
            if error:
                result["error"] = error
                result["result"] = "error"
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_keyboard_key(self, item: dict) -> dict:
        """Press one key, optionally together with a modifier."""
        key = self.get_param(item, "key", None)
        modifier = self.get_param(item, "modifier", None)
        keys = [modifier, key] if modifier else [key]
        nested = {
            "cmd": "keyboard_keys",
            "params": {
                "keys": [value for value in keys if value is not None],
                "repeat": self.get_param(item, "repeat", 1),
                "hold": self.get_param(item, "hold", 0.04),
                "key_delay": self.get_param(item, "key_delay", 0.012),
            },
        }
        if self.has_param(item, "no_screenshot"):
            nested["params"]["no_screenshot"] = self.get_param(item, "no_screenshot")
        response = self.cmd_keyboard_keys(nested)
        # Preserve the original request envelope expected by callers/rendering.
        if isinstance(response, dict):
            response["request"] = item
        return response

    def cmd_keyboard_type(self, item: dict) -> dict:
        """Type literal text and optionally press Enter."""
        keyboard = KeyboardController()
        try:
            text = str(self.get_param(item, "text", "") or "")
            if self.plugin.get_option_value("auto_focus"):
                self.set_focus()
                time.sleep(1)
            modifier = self.get_param(item, "modifier", None)
            pressed = []
            try:
                if modifier:
                    pressed = self._press_keys_down(keyboard, [modifier])
                if text:
                    keyboard.type(text)
            finally:
                self._release_keys(keyboard, pressed)
            if bool(self.get_param(item, "press_enter", False)):
                keyboard.press(Key.enter)
                keyboard.release(Key.enter)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        if self.has_param(item, "no_screenshot") and isinstance(result, dict):
            result["no_screenshot"] = True
        return self.make_response(item, result)

    def cmd_make_screenshot(self, item: dict):
        """
        Make screenshot (send signal)

        :param item: command item
        :return: response item
        """
        try:
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
        # make screenshot will be handled in the main thread (in response)
        return self.make_response(item, result)

    def set_focus(self):
        """Set focus to the current mouse position"""
        try:
            mouse = MouseController()
            mouse.click(Button.left, 1)
        except Exception as e:
            pass

    def remap_key(self, key: str) -> str:
        """
        Remap key to a specific format if needed

        :param key: key name
        :return: remapped key name
        """
        mapping = {
            "PAGEDOWN": Key.page_down,
            "PAGEUP": Key.page_up,
            "BACKSPACE": Key.backspace,
            "RETURN": Key.enter,
            "ENTER": Key.enter,
            "ESCAPE": Key.esc,
            "LEFT": Key.left,
            "RIGHT": Key.right,
            "UP": Key.up,
            "DOWN": Key.down,
            "SPACE": Key.space,
            "TAB": Key.tab,
            "CTRL": Key.ctrl,
            "CONTROL": Key.ctrl,
            "ALT": Key.alt,
            "SHIFT": Key.shift,
            "CMD": Key.cmd,
            "SUPER": Key.cmd,  # remap super key to cmd
            "START": Key.cmd,  # remap start key to cmd
            "F1": Key.f1,
            "F2": Key.f2,
            "F3": Key.f3,
            "F4": Key.f4,
            "F5": Key.f5,
            "F6": Key.f6,
            "F7": Key.f7,
            "F8": Key.f8,
            "F9": Key.f9,
            "F10": Key.f10,
            "F11": Key.f11,
            "F12": Key.f12,
            "PRINTSCREEN": Key.print_screen,
            "PRINT_SCREEN": Key.print_screen,
            "PRTSC": Key.print_screen,
            "END": Key.end,
            "HOME": Key.home,
        }
        k = key.upper() if isinstance(key, str) else key
        return mapping.get(k, key)

    def get_current(self, item: dict = None) -> dict:
        """Return current state in screenshot pixel coordinates."""
        current_step = self.get_param(item, "current_step", "")
        left, top, screen_x, screen_y = self._get_screen_geometry()
        mouse = MouseController()
        gx, gy = mouse.position
        return {
            "result": "success",
            "current_step": current_step,
            "screen_w": screen_x,
            "screen_h": screen_y,
            "mouse_x": int(gx - left),
            "mouse_y": int(gy - top),
            "url": "",
        }

    def cmd_wait_5_seconds(self, item: dict) -> dict:
        return self.cmd_wait({"cmd": "wait", "params": {"seconds": 5}})

    def cmd_go_back(self, item: dict) -> dict:
        keys = ["cmd", "["] if self._is_mac() else ["alt", "left"]
        return self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": {"keys": keys}})

    def cmd_go_forward(self, item: dict) -> dict:
        keys = ["cmd", "]"] if self._is_mac() else ["alt", "right"]
        return self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": {"keys": keys}})

    def cmd_search(self, item: dict) -> dict:
        return self.cmd_open_web_browser({"cmd": "open_web_browser", "params": {"url": "https://www.google.com"}})

    def cmd_navigate(self, item: dict) -> dict:
        url = ""
        if self.has_param(item, "url"):
            url = self.get_param(item, "url") or ""
        return self.cmd_open_web_browser({"cmd": "open_web_browser", "params": {"url": url}})

    def cmd_click_at(self, item: dict) -> dict:
        x = int(self.get_param(item, "x"))
        y = int(self.get_param(item, "y"))
        px = self._denorm_x(x)
        py = self._denorm_y(y)
        return self.cmd_mouse_move({"cmd": "mouse_move", "params": {"x": px, "y": py, "click": "left", "num_clicks": 1}})

    def cmd_hover_at(self, item: dict) -> dict:
        x = int(self.get_param(item, "x"))
        y = int(self.get_param(item, "y"))
        px = self._denorm_x(x)
        py = self._denorm_y(y)
        return self.cmd_mouse_move({"cmd": "mouse_move", "params": {"x": px, "y": py}})

    def cmd_type_text_at(self, item: dict) -> dict:
        x = int(self.get_param(item, "x"))
        y = int(self.get_param(item, "y"))
        px = self._denorm_x(x)
        py = self._denorm_y(y)
        text = self.get_param(item, "text", "") or ""
        press_enter = bool(self.get_param(item, "press_enter", True))
        clear_before = bool(self.get_param(item, "clear_before_typing", True))

        # focus field
        self.cmd_mouse_move({"cmd": "mouse_move", "params": {"x": px, "y": py, "click": "left", "num_clicks": 1}})
        if clear_before:
            keys = ["cmd", "a"] if self._is_mac() else ["ctrl", "a"]
            self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": {"keys": keys}})
            self.cmd_keyboard_key({"cmd": "keyboard_key", "params": {"key": "BACKSPACE"}})
        self.cmd_keyboard_type({"cmd": "keyboard_type", "params": {"text": text}})
        if press_enter:
            self.cmd_keyboard_key({"cmd": "keyboard_key", "params": {"key": "ENTER"}})
        return self.make_response(item, self.get_current(item))

    def cmd_key_combination(self, item: dict) -> dict:
        """Compatibility alias for a true simultaneous key chord."""
        params = dict(item.get("params", {}))
        raw = params.get("keys", [])
        params["keys"] = self._parse_keys(raw)
        response = self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": params})
        if isinstance(response, dict):
            response["request"] = item
        return response

    def cmd_scroll_document(self, item: dict) -> dict:
        direction = str(self.get_param(item, "direction", "down")).lower()
        magnitude = int(self.get_param(item, "magnitude", 800))
        dx, dy = 0, 0
        if direction == "down":
            dy = magnitude
        elif direction == "up":
            dy = -magnitude
        elif direction == "left":
            dx = -magnitude
        elif direction == "right":
            dx = magnitude
        return self.cmd_mouse_scroll({"cmd": "mouse_scroll", "params": {"dx": dx, "dy": dy, "unit": "px"}})

    def cmd_scroll_at(self, item: dict) -> dict:
        direction = str(self.get_param(item, "direction", "down")).lower()
        magnitude = int(self.get_param(item, "magnitude", 800))
        x = self.get_param(item, "x", None)
        y = self.get_param(item, "y", None)
        px = self._denorm_x(int(x)) if x is not None else None
        py = self._denorm_y(int(y)) if y is not None else None
        dx, dy = 0, 0
        if direction == "down":
            dy = magnitude
        elif direction == "up":
            dy = -magnitude
        elif direction == "left":
            dx = -magnitude
        elif direction == "right":
            dx = magnitude
        payload = {"dx": dx, "dy": dy, "unit": "px"}
        if px is not None and py is not None:
            payload["x"] = px
            payload["y"] = py
        return self.cmd_mouse_scroll({"cmd": "mouse_scroll", "params": payload})

    def cmd_drag_and_drop(self, item: dict) -> dict:
        x = int(self.get_param(item, "x"))
        y = int(self.get_param(item, "y"))
        dx = int(self.get_param(item, "destination_x"))
        dy = int(self.get_param(item, "destination_y"))
        return self.cmd_mouse_drag({
            "cmd": "mouse_drag",
            "params": {
                "x": self._denorm_x(x),
                "y": self._denorm_y(y),
                "dx": self._denorm_x(dx),
                "dy": self._denorm_y(dy),
            }
        })

    # ========================= Action-style convenience ========================= #

    def cmd_click(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "mouse_click"
        return self.cmd_mouse_click(item2)

    def cmd_double_click(self, item: dict) -> dict:
        item2 = dict(item)
        p = dict(item.get("params", {}))
        p["num_clicks"] = 2
        item2["params"] = p
        item2["cmd"] = "mouse_click"
        return self.cmd_mouse_click(item2)

    def cmd_move(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "mouse_move"
        return self.cmd_mouse_move(item2)

    def cmd_type_text(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "keyboard_type"
        return self.cmd_keyboard_type(item2)

    def cmd_keypress(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "keyboard_keys"
        return self.cmd_keyboard_keys(item2)

    def cmd_scroll(self, item: dict) -> dict:
        item2 = dict(item)
        p = dict(item.get("params", {}))
        p["dx"] = int(p.get("scroll_x", p.get("dx", 0)) or 0)
        p["dy"] = int(p.get("scroll_y", p.get("dy", 0)) or 0)
        p.setdefault("unit", "px")
        item2["params"] = p
        item2["cmd"] = "mouse_scroll"
        return self.cmd_mouse_scroll(item2)

    def cmd_drag(self, item: dict) -> dict:
        item2 = dict(item)
        item2["cmd"] = "mouse_drag"
        return self.cmd_mouse_drag(item2)

    def cmd_mouse_down(self, item: dict) -> dict:
        try:
            mouse = MouseController()
            x, y = self.get_param(item, "x", None), self.get_param(item, "y", None)
            if x is not None and y is not None:
                mouse.position = self._to_screen_point(item, x, y)
            button_name = str(self.get_param(item, "button", "left") or "left").lower()
            button = Button.right if button_name == "right" else Button.middle if button_name == "middle" else Button.left
            self._with_mouse_modifiers(item, lambda: mouse.press(button))
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_mouse_up(self, item: dict) -> dict:
        try:
            mouse = MouseController()
            x, y = self.get_param(item, "x", None), self.get_param(item, "y", None)
            if x is not None and y is not None:
                mouse.position = self._to_screen_point(item, x, y)
            button_name = str(self.get_param(item, "button", "left") or "left").lower()
            button = Button.right if button_name == "right" else Button.middle if button_name == "middle" else Button.left
            mouse.release(button)
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_key_down(self, item: dict) -> dict:
        try:
            key = self.remap_key(self.get_param(item, "key"))
            KeyboardController().press(key)
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_key_up(self, item: dict) -> dict:
        try:
            key = self.remap_key(self.get_param(item, "key"))
            KeyboardController().release(key)
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_hold_key(self, item: dict) -> dict:
        keyboard = KeyboardController()
        pressed = []
        try:
            keys = self.get_param(item, "keys", self.get_param(item, "key", []))
            duration = max(0.0, min(300.0, float(self.get_param(item, "duration", 1) or 1)))
            pressed = self._press_keys_down(keyboard, keys if isinstance(keys, list) else self._parse_keys(keys))
            time.sleep(duration)
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        finally:
            self._release_keys(keyboard, pressed)
        return self.make_response(item, result)

    def cmd_long_press(self, item: dict) -> dict:
        try:
            mouse = MouseController()
            x, y = self._to_screen_point(item, self.get_param(item, "x"), self.get_param(item, "y"))
            mouse.position = (x, y)
            duration = max(0.0, min(300.0, float(
                self.get_param(item, "duration", self.get_param(item, "seconds", 2)) or 2
            )))
            mouse.press(Button.left)
            try:
                time.sleep(duration)
            finally:
                mouse.release(Button.left)
            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

