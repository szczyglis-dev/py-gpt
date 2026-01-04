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

import sys
import time

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    screenshot = Signal(dict, object)


class Worker(BaseWorker):
    """
    Host worker: executes computer-use actions using native OS input (pynput).
    It supports the full set of Computer Use commands. Each response includes "url" (empty on host).
    """

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

                    # open web browser
                    if cmd == "open_web_browser":
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

                    if response:
                        responses.append(response)

                except Exception as e:
                    responses.append(
                        self.make_response(
                            item,
                            self.throw_error(e)
                        )
                    )

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

    def _get_screen_size(self) -> tuple:
        screen = self.window.app.primaryScreen()
        size = screen.size()
        return size.width(), size.height()

    def _denorm_x(self, x_norm: int) -> int:
        w, _ = self._get_screen_size()
        x_norm = max(0, min(999, int(x_norm)))
        return int(round(x_norm / 1000.0 * w))

    def _denorm_y(self, y_norm: int) -> int:
        _, h = self._get_screen_size()
        y_norm = max(0, min(999, int(y_norm)))
        return int(round(y_norm / 1000.0 * h))

    def _is_normalized_pair(self, x, y) -> bool:
        try:
            xi, yi = int(x), int(y)
            return 0 <= xi <= 999 and 0 <= yi <= 999
        except Exception:
            return False

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
        """
        Set mouse position

        :param item: command item
        :return: response item
        """
        error = None
        click = None
        num_clicks = 1
        x = 0
        y = 0
        if self.has_param(item, "x"):
            x = self.get_param(item, "x")
        elif self.has_param(item, "mouse_x"):
            x = self.get_param(item, "mouse_x")
        if self.has_param(item, "y"):
            y = self.get_param(item, "y")
        elif self.has_param(item, "mouse_y"):
            y = self.get_param(item, "mouse_y")

        # accept normalized 0..999
        try:
            if self._is_normalized_pair(x, y):
                x = self._denorm_x(int(x))
                y = self._denorm_y(int(y))
        except Exception:
            pass

        if self.has_param(item, "click"):
            click = self.get_param(item, "click")
        if self.has_param(item, "num_clicks"):
            num_clicks = int(self.get_param(item, "num_clicks"))
        try:
            mouse = MouseController()
            mouse.position = (int(x), int(y))
            if click:
                time.sleep(0.05)
                self.cmd_mouse_click({
                    "cmd": "mouse_click",
                    "params": {
                        "button": click,
                        "num_clicks": num_clicks,
                        "x": int(x),
                        "y": int(y),
                    }
                })
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

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_mouse_click(self, item: dict) -> dict:
        """
        Mouse click

        :param item: command item
        :return: response item
        """
        button = Button.left
        num = 1
        x = None
        y = None
        if self.has_param(item, "button"):
            btn_name = self.get_param(item, "button")
            if isinstance(btn_name, str):
                if btn_name.lower() == "middle":
                    button = Button.middle
                elif btn_name.lower() == "right":
                    button = Button.right
        if self.has_param(item, "num_clicks"):
            num = int(self.get_param(item, "num_clicks"))
        if self.has_param(item, "x") and self.has_param(item, "y"):
            x = int(self.get_param(item, "x"))
            y = int(self.get_param(item, "y"))
            if self._is_normalized_pair(x, y):
                x = self._denorm_x(x)
                y = self._denorm_y(y)
        try:
            mouse = MouseController()
            if x is not None and y is not None:
                mouse.position = (x, y)
                time.sleep(0.05)
            mouse.click(button, max(1, num))
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_mouse_scroll(self, item: dict) -> dict:
        """
        Mouse scroll

        :param item: command item
        :return: response item
        """
        x = None
        y = None
        if self.has_param(item, "x"):
            x = self.get_param(item, "x")
        elif self.has_param(item, "mouse_x"):
            x = self.get_param(item, "mouse_x")
        if self.has_param(item, "y"):
            y = self.get_param(item, "y")
        elif self.has_param(item, "mouse_y"):
            y = self.get_param(item, "mouse_y")
        if x is not None and y is not None:
            try:
                # accept normalized 0..999
                xi, yi = int(x), int(y)
                if self._is_normalized_pair(xi, yi):
                    xi = self._denorm_x(xi)
                    yi = self._denorm_y(yi)
                mouse = MouseController()
                mouse.position = (xi, yi)
                time.sleep(0.05)
            except Exception as e:
                error = str(e)
                self.log("Error: {}".format(e))
        dx = 0
        dy = 0
        unit = "step"
        conversion_factor = 30
        delay = 0.01
        if self.has_param(item, "dx"):
            dx = int(self.get_param(item, "dx"))
        if self.has_param(item, "dy"):
            dy = int(self.get_param(item, "dy"))
        if self.has_param(item, "unit"):
            tmp_unit = self.get_param(item, "unit")
            if tmp_unit in ["step", "px"]:
                unit = tmp_unit
        try:
            notches_x = 0
            notches_y = 0
            mouse = MouseController()
            if unit == "step":
                notches_x = dx
                notches_y = dy
            elif unit == "px":
                notches_x = int(round(dx / conversion_factor))
                notches_y = int(round(dy / conversion_factor))

            # scroll x
            for _ in range(abs(notches_x)):
                sdx = 1 if notches_x > 0 else -1
                mouse.scroll(sdx, 0)
                time.sleep(delay)

            # scroll y
            for _ in range(abs(notches_y)):
                sdy = 1 if notches_y > 0 else -1
                mouse.scroll(0, sdy)
                time.sleep(delay)

            print("scrolling: dx={}, dy={}".format(dx, dy))
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_mouse_drag(self, item: dict) -> dict:
        """
        Mouse drag

        :param item: command item
        :return: response item
        """
        x = None
        y = None
        if self.has_param(item, "x"):
            x = int(self.get_param(item, "x"))
        elif self.has_param(item, "mouse_x"):
            x = int(self.get_param(item, "mouse_x"))
        if self.has_param(item, "y"):
            y = int(self.get_param(item, "y"))
        elif self.has_param(item, "mouse_y"):
            y = int(self.get_param(item, "mouse_y"))
        if x is not None and y is not None:
            try:
                if self._is_normalized_pair(x, y):
                    x = self._denorm_x(x)
                    y = self._denorm_y(y)
                mouse = MouseController()
                mouse.position = (x, y)
                time.sleep(0.05)
            except Exception as e:
                error = str(e)
                self.log("Error: {}".format(e))
        dx = 0
        dy = 0
        delay = 0.02
        if self.has_param(item, "dx"):
            dx = int(self.get_param(item, "dx"))
        if self.has_param(item, "dy"):
            dy = int(self.get_param(item, "dy"))
        try:
            # If dx,dy are normalized destination, convert
            if self._is_normalized_pair(dx, dy):
                dx = self._denorm_x(dx)
                dy = self._denorm_y(dy)
            mouse = MouseController()
            mouse.press(Button.left)
            time.sleep(delay)
            mouse.position = (dx, dy)  # absolute destination
            time.sleep(delay)
            mouse.release(Button.left)
            print("dragging: dx={}, dy={}".format(dx, dy))
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_keyboard_keys(self, item: dict) -> dict:
        """
        Keyboard keys press (sequence, single modifier supported)
        For multiple modifiers use key_combination.
        """
        keyboard = KeyboardController()
        error = None
        keys_list = []
        modifier = None
        modifiers_list = [
            "ctrl", "control", "alt", "shift", "cmd", "super"
        ]
        if self.has_param(item, "keys"):
            keys = self.get_param(item, "keys")
            for key in keys:
                if isinstance(key, str):
                    if key.lower() in modifiers_list and modifier is None:
                        # check if key is modifier
                        if key.lower() == "ctrl" or key.lower() == "control":
                            modifier = Key.ctrl
                        elif key.lower() == "alt":
                            modifier = Key.alt
                        elif key.lower() == "shift":
                            modifier = Key.shift
                        elif key.lower() == "cmd":
                            modifier = Key.cmd
                        elif key.lower() == "super" or key.lower() == "start":
                            modifier = Key.cmd
                    else:
                        keys_list.append(self.remap_key(key))  # remap key if needed

        # autofocus on the window
        if self.plugin.get_option_value("auto_focus"):
            self.set_focus()
            time.sleep(1)  # wait for a second

        try:
            if modifier:
                with keyboard.pressed(modifier):
                    for key in keys_list:
                        keyboard.press(key)
                        keyboard.release(key)
                        time.sleep(0.1)
            else:
                for key in keys_list:
                    keyboard.press(key)
                    keyboard.release(key)
                    time.sleep(0.1)

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

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        return self.make_response(item, result)

    def cmd_keyboard_key(self, item: dict) -> dict:
        """
        Keyboard key press

        :param item: command item
        :return: response item
        """
        keyboard = KeyboardController()
        error = None
        if self.has_param(item, "key"):
            key = self.get_param(item, "key")
            modifier = None
            if self.has_param(item, "modifier"):
                tmp_modifier = self.get_param(item, "modifier")
                if tmp_modifier.lower() == "ctrl" or tmp_modifier.lower() == "control":
                    modifier = Key.ctrl
                elif tmp_modifier.lower() == "alt":
                    modifier = Key.alt
                elif tmp_modifier.lower() == "shift":
                    modifier = Key.shift
                elif tmp_modifier.lower() == "cmd":
                    modifier = Key.cmd

            # autofocus on the window
            if self.plugin.get_option_value("auto_focus"):
                self.set_focus()
                time.sleep(1)  # wait for a second

            if isinstance(key, str) and (key.lower() == "super" or key.lower() == "start"):
                key = Key.cmd

            key = self.remap_key(key)  # remap key if needed
            try:
                if modifier:
                    with keyboard.pressed(modifier):
                        keyboard.press(key)
                        keyboard.release(key)
                else:
                    keyboard.press(key)
                    keyboard.release(key)
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

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True


        return self.make_response(item, result)

    def cmd_keyboard_type(self, item: dict) -> dict:
        """
        Keyboard type text

        :param item: command item
        :return: response item
        """
        keyboard = KeyboardController()
        if self.has_param(item, "text"):
            text = self.get_param(item, "text")
            modifier = None
            if self.has_param(item, "modifier"):
                tmp_modifier = self.get_param(item, "modifier")
                if tmp_modifier.lower() == "ctrl" or tmp_modifier.lower() == "control":
                    modifier = Key.ctrl
                elif tmp_modifier.lower() == "alt":
                    modifier = Key.alt
                elif tmp_modifier.lower() == "shift":
                    modifier = Key.shift
                elif tmp_modifier.lower() == "cmd":
                    modifier = Key.cmd

            # autofocus on the window
            if self.plugin.get_option_value("auto_focus"):
                self.set_focus()
                time.sleep(1)  # wait for a second

            if modifier:
                with keyboard.pressed(modifier):
                    keyboard.type(text)
            else:
                keyboard.type(text)

        try:
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
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
        """
        Get current mouse position and screen resolution

        :param item: command item
        :return: coordinates and screen resolution
        """
        current_step = self.get_param(item, "current_step", "")
        screen = self.window.app.primaryScreen()
        size = screen.size()
        screen_x = size.width()
        screen_y = size.height()
        mouse = MouseController()
        mouse_pos_x, mouse_pos_y = mouse.position
        return {
            "result": "success",
            'current_step': current_step,
            'screen_w': screen_x,
            'screen_h': screen_y,
            'mouse_x': mouse_pos_x,
            'mouse_y': mouse_pos_y,
            'url': "",  # host has no sandbox browser URL
        }

    # ========================= New Computer Use commands (host-native) ========================= #

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
        keyboard = KeyboardController()
        error = None

        # autofocus on the window
        if self.plugin.get_option_value("auto_focus"):
            self.set_focus()
            time.sleep(1)

        try:
            raw = self.get_param(item, "keys", [])
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.replace("+", " ").split() if p.strip()]
            else:
                parts = list(raw or [])

            # Separate modifiers
            mods_map = {
                "ctrl": Key.ctrl, "control": Key.ctrl,
                "alt": Key.alt, "shift": Key.shift,
                "cmd": Key.cmd, "super": Key.cmd, "start": Key.cmd,
            }
            modifiers = []
            keys = []
            for p in parts:
                pl = p.lower()
                if pl in mods_map and mods_map[pl] not in modifiers:
                    modifiers.append(mods_map[pl])
                else:
                    keys.append(self.remap_key(p))

            for m in modifiers:
                keyboard.press(m)
            for k in keys:
                keyboard.press(k)
                keyboard.release(k)
            for m in reversed(modifiers):
                keyboard.release(m)

            result = self.get_current(item)
        except Exception as e:
            result = self.throw_error(e)

        return self.make_response(item, result)

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
        p = dict(item.get("params", {}))
        x = p.get("x", None)
        y = p.get("y", None)
        if x is not None and y is not None and self._is_normalized_pair(x, y):
            p["x"] = self._denorm_x(int(x))
            p["y"] = self._denorm_y(int(y))
        p["num_clicks"] = int(p.get("num_clicks", 1))
        return self.cmd_mouse_click({"cmd": "mouse_click", "params": p})

    def cmd_double_click(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        p["num_clicks"] = 2
        return self.cmd_click({"cmd": "click", "params": p})

    def cmd_move(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        if "x" in p and "y" in p and self._is_normalized_pair(p["x"], p["y"]):
            p["x"] = self._denorm_x(int(p["x"]))
            p["y"] = self._denorm_y(int(p["y"]))
        return self.cmd_mouse_move({"cmd": "mouse_move", "params": p})

    def cmd_type_text(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        return self.cmd_keyboard_type({"cmd": "keyboard_type", "params": p})

    def cmd_keypress(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        return self.cmd_keyboard_keys({"cmd": "keyboard_keys", "params": p})

    def cmd_scroll(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        # accept scroll_x/scroll_y aliases
        if "scroll_x" in p:
            p["dx"] = int(p.get("scroll_x", 0))
        if "scroll_y" in p:
            p["dy"] = int(p.get("scroll_y", 0))
        p["unit"] = "px"
        # normalize optional pointer position
        if "x" in p and "y" in p and self._is_normalized_pair(p["x"], p["y"]):
            p["x"] = self._denorm_x(int(p["x"]))
            p["y"] = self._denorm_y(int(p["y"]))
        return self.cmd_mouse_scroll({"cmd": "mouse_scroll", "params": p})

    def cmd_drag(self, item: dict) -> dict:
        p = dict(item.get("params", {}))
        path = p.get("path", None)
        if path and isinstance(path, list) and len(path) >= 2:
            x0 = int(path[0]["x"]); y0 = int(path[0]["y"])
            x1 = int(path[1]["x"]); y1 = int(path[1]["y"])
            if self._is_normalized_pair(x0, y0):
                x0 = self._denorm_x(x0); y0 = self._denorm_y(y0)
            if self._is_normalized_pair(x1, y1):
                x1 = self._denorm_x(x1); y1 = self._denorm_y(y1)
            return self.cmd_mouse_drag({"cmd": "mouse_drag", "params": {"x": x0, "y": y0, "dx": x1, "dy": y1}})
        # fallback: explicit x,y and dx,dy
        if "x" in p and "y" in p and "dx" in p and "dy" in p:
            x0 = int(p["x"]); y0 = int(p["y"]); x1 = int(p["dx"]); y1 = int(p["dy"])
            if self._is_normalized_pair(x0, y0):
                x0 = self._denorm_x(x0); y0 = self._denorm_y(y0)
            if self._is_normalized_pair(x1, y1):
                x1 = self._denorm_x(x1); y1 = self._denorm_y(y1)
            return self.cmd_mouse_drag({"cmd": "mouse_drag", "params": {"x": x0, "y": y0, "dx": x1, "dy": y1}})
        return self.make_response(item, self.get_current(item))