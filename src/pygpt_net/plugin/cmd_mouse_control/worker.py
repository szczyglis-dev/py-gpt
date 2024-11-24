#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 04:00:00                  #
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

                    # keyboard type
                    elif item["cmd"] == "keyboard_type":
                        if self.plugin.get_option_value("allow_keyboard"):
                            response = self.cmd_keyboard_type(item)

                    if response:
                        responses.append(response)

            except Exception as e:
                responses.append(
                    self.make_response(
                        item,
                        self.throw_error(e)
                    )
                )

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

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
        return self.make_response(item, result)

    def cmd_mouse_move(self, item: dict) -> dict:
        """
        Set mouse position

        :param item: command item
        :return: response item
        """
        error = None
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
        try:
            mouse = MouseController()
            mouse.position = (x, y)
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
            if btn_name == "middle":
                button = Button.middle
            elif btn_name == "right":
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
        return self.make_response(item, result)

    def cmd_mouse_scroll(self, item: dict) -> dict:
        """
        Mouse scroll

        :param item: command item
        :return: response item
        """
        x = 0
        y = 0
        if self.has_param(item, "dx"):
            x = self.get_param(item, "dx")
        if self.has_param(item, "dy"):
            y = self.get_param(item, "dy")
        try:
            mouse = MouseController()
            mouse.scroll(x, y)
            result = self.get_current(item)
            self.log("Response: {}".format(result))
        except Exception as e:
            result = self.throw_error(e)
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
                if tmp_modifier == "ctrl":
                    modifier = Key.ctrl
                elif tmp_modifier == "alt":
                    modifier = Key.alt
                elif tmp_modifier == "shift":
                    modifier = Key.shift
                elif tmp_modifier == "cmd":
                    modifier = Key.cmd

            # autofocus on the window
            if self.plugin.get_option_value("auto_focus"):
                self.set_focus()
                time.sleep(1)  # wait for a second

            if key == "super" or key == "start":
                key = Key.cmd

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
                if tmp_modifier == "ctrl":
                    modifier = Key.ctrl
                elif tmp_modifier == "alt":
                    modifier = Key.alt
                elif tmp_modifier == "shift":
                    modifier = Key.shift
                elif tmp_modifier == "cmd":
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
