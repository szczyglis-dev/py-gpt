#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.09 02:00:00                  #
# ================================================== #

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base import BaseWorker, BaseSignals


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
            response = None
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                    # get mouse position
                    if item["cmd"] == "mouse_get_pos":
                        response = self.cmd_mouse_get_pos(item)

                    # set mouse position
                    elif item["cmd"] == "mouse_set_pos":
                        if self.plugin.get_option_value("allow_mouse_move"):
                            response = self.cmd_mouse_set_pos(item)

                    # move mouse position
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
                    elif item["cmd"] == "make_screenshot":
                        if self.plugin.get_option_value("allow_screenshot"):
                            self.cmd_make_screenshot(item)
                        # return here - this will be handled by main thread
                        return

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
                responses.append({
                    "request": {
                        "cmd": item["cmd"],
                    },
                    "result": "Error {}".format(e),
                })
                self.error(e)
                self.log("Error: {}".format(e))

        if self.msg is not None:
            self.status(self.msg)

        # send response
        if len(responses) > 0:
            # return only first response
            for response in responses:
                self.reply(response)
                break

    def cmd_mouse_get_pos(self, item: dict) -> dict:
        """
        Get mouse position

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            self.msg = "Mouse get position"
            self.log(self.msg)
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_mouse_set_pos(self, item: dict) -> dict:
        """
        Set mouse position

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)

        x = 0
        y = 0
        if "params" in item:
            if "x" in item["params"]:
                x = item["params"]["x"]
            if "y" in item["params"]:
                y = item["params"]["y"]
        mouse = MouseController()
        mouse.position = (x, y)

        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_mouse_move(self, item: dict) -> dict:
        """
        Move mouse position

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)

        x = 0
        y = 0
        if "params" in item:
            if "offset_x" in item["params"]:
                x = item["params"]["offset_x"]
            if "offset_y" in item["params"]:
                y = item["params"]["offset_y"]
        mouse = MouseController()
        mouse.move = (x, y)

        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_mouse_click(self, item: dict) -> dict:
        """
        Mouse click

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)

        button = Button.left
        num = 1
        if "params" in item:
            if "button" in item["params"]:
                btn_name = item["params"]["button"]
                if btn_name == "middle":
                    button = Button.middle
                elif btn_name == "right":
                    button = Button.right
            if "num_clicks" in item["params"]:
                num = item["params"]["num_clicks"]
        mouse = MouseController()
        mouse.click(button, num)

        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_mouse_scroll(self, item: dict) -> dict:
        """
        Mouse scroll

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)

        x = 0
        y = 0
        if "params" in item:
            if "dx" in item["params"]:
                x = item["params"]["dx"]
            if "dy" in item["params"]:
                y = item["params"]["dy"]
        mouse = MouseController()
        mouse.scroll(x, y)
        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_keyboard_key(self, item: dict) -> dict:
        """
        Keyboard key press

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        keyboard = KeyboardController()
        if "params" in item:
            if "key" in item["params"]:
                key = item["params"]["key"]
                modifier = None
                if "modifier" in item["params"]:
                    tmp_modifier = item["params"]["modifier"]
                    if tmp_modifier == "ctrl":
                        modifier = Key.ctrl
                    elif tmp_modifier == "alt":
                        modifier = Key.alt
                    elif tmp_modifier == "shift":
                        modifier = Key.shift
                    elif tmp_modifier == "cmd":
                        modifier = Key.cmd
                if modifier:
                    with keyboard.pressed(modifier):
                        keyboard.press(key)
                        keyboard.release(key)
                else:
                    keyboard.press(key)
                    keyboard.release(key)

        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_keyboard_type(self, item: dict) -> dict:
        """
        Keyboard key press

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        keyboard = KeyboardController()
        if "params" in item:
            if "text" in item["params"]:
                text = item["params"]["text"]
                modifier = None
                if "modifier" in item["params"]:
                    tmp_modifier = item["params"]["modifier"]
                    if tmp_modifier == "ctrl":
                        modifier = Key.ctrl
                    elif tmp_modifier == "alt":
                        modifier = Key.alt
                    elif tmp_modifier == "shift":
                        modifier = Key.shift
                    elif tmp_modifier == "cmd":
                        modifier = Key.cmd
                if modifier:
                    with keyboard.pressed(modifier):
                        keyboard.type(text)
                else:
                    keyboard.type(text)

        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_make_screenshot(self, item: dict):
        """
        Make screenshot (send signal)

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            data = self.get_current()
            self.log("Response: {}".format(data))
            response = {
                "request": request,
                "result": data,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))

        self.signals.screenshot.emit(response, self.ctx)  # use signal - this will be handled by main thread

    def get_current(self) -> dict:
        """
        Get current mouse position and screen resolution

        :return: coordinates and screen resolution
        """
        screen = self.window.app.primaryScreen()
        size = screen.size()
        screen_x = size.width()
        screen_y = size.height()
        mouse = MouseController()
        mouse_pos_x, mouse_pos_y = mouse.position
        return {
            'screen_width': screen_x,
            'screen_height': screen_y,
            'mouse_pos_x': mouse_pos_x, 
            'mouse_pos_y': mouse_pos_y,
        }

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}
