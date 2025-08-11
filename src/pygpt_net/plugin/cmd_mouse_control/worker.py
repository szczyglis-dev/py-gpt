#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 14:00:00                  #
# ================================================== #

import time

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    screenshot = Signal(dict, object)


class Worker(BaseWorker):
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
                    if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):
                        # get mouse position
                        if item["cmd"] == "get_mouse_position":
                            response = self.cmd_mouse_get_pos(item)

                        # set mouse position
                        elif item["cmd"] == "mouse_move":
                            if self.plugin.get_option_value("allow_mouse_move"):
                                response = self.cmd_mouse_move(item)

                        # drag mouse
                        elif item["cmd"] == "mouse_drag":
                            if self.plugin.get_option_value("allow_mouse_move"):
                                response = self.cmd_mouse_drag(item)

                        # mouse click
                        elif item["cmd"] == "mouse_click":
                            if self.plugin.get_option_value("allow_mouse_click"):
                                response = self.cmd_mouse_click(item)

                        # mouse scroll
                        elif item["cmd"] == "mouse_scroll":
                            if self.plugin.get_option_value("allow_mouse_scroll"):
                                response = self.cmd_mouse_scroll(item)

                        # screenshot
                        elif item["cmd"] == "get_screenshot":
                            if self.plugin.get_option_value("allow_screenshot"):
                                response = self.cmd_make_screenshot(item)

                        # keyboard key
                        elif item["cmd"] == "keyboard_key":
                            if self.plugin.get_option_value("allow_keyboard"):
                                response = self.cmd_keyboard_key(item)

                        # keyboard key
                        elif item["cmd"] == "keyboard_keys":
                            if self.plugin.get_option_value("allow_keyboard"):
                                response = self.cmd_keyboard_keys(item)

                        # keyboard type
                        elif item["cmd"] == "keyboard_type":
                            if self.plugin.get_option_value("allow_keyboard"):
                                response = self.cmd_keyboard_type(item)

                        # wait
                        elif item["cmd"] == "wait":
                            response = self.cmd_wait(item)

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
                self.reply_more(responses) # send response

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def on_destroy(self):
        """Handle destroyed event."""
        self.cleanup()

    def cmd_wait(self, item: dict) -> dict:
        """
        Wait

        :param item: command item
        :return: response item
        """
        try:
            self.msg = "Wait"
            self.log(self.msg)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)

        # disable returning screenshot if requested
        if self.has_param(item, "no_screenshot"):
            result["no_screenshot"] = True

        time.sleep(2)
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

        if self.has_param(item, "click"):
            click = self.get_param(item, "click")
        if self.has_param(item, "num_clicks"):
            num_clicks = int(self.get_param(item, "num_clicks"))
        try:
            mouse = MouseController()
            mouse.position = (x, y)
            if click:
                time.sleep(0.5)  # wait for a moment before clicking
                self.cmd_mouse_click({
                    "cmd": "mouse_click",
                    "params": {
                        "button": click,
                        "num_clicks": num_clicks,
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
        if self.has_param(item, "button"):
            btn_name = self.get_param(item, "button")
            if btn_name.lower() == "middle":
                button = Button.middle
            elif btn_name.lower() == "right":
                button = Button.right
        if self.has_param(item, "num_clicks"):
            num = int(self.get_param(item, "num_clicks"))
        try:
            mouse = MouseController()
            mouse.click(button, num)
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
                mouse = MouseController()
                mouse.position = (x, y)
                time.sleep(0.5)  # wait for a moment before scrolling
            except Exception as e:
                error = str(e)
                self.log("Error: {}".format(e))
        dx = 0
        dy = 0
        unit = "step"
        conversion_factor = 30
        delay = 0.01
        if self.has_param(item, "dx"):
            dx = self.get_param(item, "dx")
        if self.has_param(item, "dy"):
            dy = self.get_param(item, "dy")
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
                dx = 1 if notches_x > 0 else -1
                mouse.scroll(dx, 0)
                time.sleep(delay)

            # scroll y
            for _ in range(abs(notches_y)):
                dy = 1 if notches_y > 0 else -1
                mouse.scroll(0, dy)
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
                mouse = MouseController()
                mouse.position = (x, y)
                time.sleep(0.5)  # wait for a moment before scrolling
            except Exception as e:
                error = str(e)
                self.log("Error: {}".format(e))
        dx = 0
        dy = 0
        delay = 0.02
        if self.has_param(item, "dx"):
            dx = self.get_param(item, "dx")
        if self.has_param(item, "dy"):
            dy = self.get_param(item, "dy")
        try:
            mouse = MouseController()
            mouse.press(Button.left)
            time.sleep(delay)
            mouse.position = (dx, dy)  # move to the new position
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
        Keyboard keys press

        :param item: command item
        :return: response item
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
                    if key.lower() in modifiers_list:
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

            if key.lower() == "super" or key.lower() == "start":
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
        Keyboard key press

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
        k = key.upper()
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
            'current_step': current_step,
            'screen_w': screen_x,
            'screen_h': screen_y,
            'mouse_x': mouse_pos_x,
            'mouse_y': mouse_pos_y,
        }
