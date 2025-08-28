#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
# ================================================== #

import base64
import json
from typing import Callable

from agents import (
    Computer,
    Environment,
    Button,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from .utils import (
    create_response,
    pp,
    sanitize_message,
)

class LocalComputer(Computer):
    """A local computer, connected to plugin cmd_mouse_control"""

    PLUGIN_ID = "cmd_mouse_control"

    def __init__(self, window):
        """
        Initialize the LocalComputer instance.

        :param window: The window instance
        """
        super().__init__()
        self.window = window

    @property
    def environment(self) -> Environment:
        """
        Get the current environment of the computer.

        :return: Environment of the computer, such as "mac", "windows", "ubuntu", or "browser".
        """
        return self.window.core.gpt.computer.get_current_env()

    @property
    def dimensions(self) -> tuple[int, int]:
        """
        Get the dimensions of the primary screen.

        :return: Tuple containing the width and height of the primary screen.
        """
        screen = self.window.app.primaryScreen()
        size = screen.size()
        screen_x = size.width()
        screen_y = size.height()
        return screen_x, screen_y

    def call_cmd(self, item: dict):
        """
        Call command via plugin

        :param item: The command item to be executed.
        """
        self.window.core.plugins.get(self.PLUGIN_ID).handle_call(item)

    def screenshot(self) -> str:
        """
        Capture screenshot of the viewport and return it as a base64 encoded string.

        :return: Base64 encoded screenshot of the viewport.
        """
        print("Taking screenshot of the viewport...")
        self.window.controller.attachment.clear_silent()
        path = self.window.controller.painter.capture.screenshot(attach_cursor=True,
                                                                 silent=True)  # attach screenshot
        with open(path, "rb") as image_file:
            data = base64.b64encode(image_file.read()).decode('utf-8')
        self.window.controller.attachment.clear_silent()
        return data

    def click(self, x: int, y: int, button: Button = "left") -> None:
        """
        Perform a mouse click at the specified coordinates (x, y) with the given button.

        :param x: x coordinate to click at.
        :param y: y coordinate to click at.
        :param button: Button to click (default is "left").
        """
        item = {
            "cmd": "mouse_move",
            "params": {
                "x": x,
                "y": y,
                "click": str(button),
                "num_clicks": 1,
            }
        }
        self.call_cmd(item)

    def double_click(self, x: int, y: int) -> None:
        """
        Perform a double-click at the specified coordinates (x, y).

        :param x: x coordinate to double-click at.
        :param y: y coordinate to double-click at.
        """
        item = {
            "cmd": "mouse_move",
            "params": {
                "x": x,
                "y": y,
                "click": "left",
                "num_clicks": 2,
            }
        }
        self.call_cmd(item)

    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """
        Scroll the mouse at the specified coordinates (x, y) with the given scroll amounts.

        :param x: x coordinate to scroll at.
        :param y: y coordinate to scroll at.
        :param scroll_x: x scroll amount (positive for right, negative for left).
        :param scroll_y: y scroll amount (positive for down, negative for up).
        """
        item = {
            "cmd": "mouse_scroll",
            "params": {
                "x": x,
                "y": y,
                "dx": scroll_x,
                "dy": -scroll_y,  # invert scroll direction
                "unit": "px",
            }
        }
        self.call_cmd(item)

    def type(self, text: str) -> None:
        """
        Type the specified text using the keyboard.

        :param text: The text to type.
        """
        item = {
            "cmd": "keyboard_type",
            "params": {
                "text": text,
            }
        }
        self.call_cmd(item)

    def wait(self) -> None:
        """Wait for a specified time (default is 1 second) before executing the next command."""
        item = {
            "cmd": "wait",
            "params": {}
        }
        self.call_cmd(item)

    def move(self, x: int, y: int) -> None:
        """
        Move the mouse to the specified coordinates (x, y).

        :param x: x coordinate to move the mouse to.
        :param y: y coordinate to move the mouse to.
        """
        item = {
            "cmd": "mouse_move",
            "params": {
                "x": x,
                "y": y,
            }
        }
        self.call_cmd(item)

    def keypress(self, keys: list[str]) -> None:
        """
        Press a list of keys on the keyboard.
        :param keys: A list of keys to press, e.g. ["Shift", "A", "B"].
        """
        item = {
            "cmd": "keyboard_keys",
            "params": {
                "keys": keys, # multiple at once
            }
        }
        self.call_cmd(item)

    def drag(self, path: list[tuple[int, int]]) -> None:
        """
        Drag the mouse along a path defined by a list of (x, y) tuples.

        :param path: A list of tuples where each tuple contains the x and y coordinates.
        """
        if not path:
            return
        x = path[0][0]
        y = path[0][1]
        dx = path[1][0]
        dy = path[1][1]
        item = {
            "cmd": "mouse_drag",
            "params": {
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
            }
        }
        self.call_cmd(item)


class Agent:
    """
    A sample agent class that can be used to interact with a computer.

    Based on: https://github.com/openai/openai-cua-sample-app/blob/main/agent/agent.py

    (See simple_cua_loop.py for a simple example without an agent.)
    """

    def __init__(
        self,
        model="computer-use-preview",
        computer: LocalComputer = None,
        tools: list[dict] = [],
        acknowledge_safety_check_callback: Callable = lambda: False,
        ctx: CtxItem = None,
        stream: bool = False,
        bridge: ConnectionContext = None,
    ):
        self.model = model
        self.computer = computer
        self.tools = tools
        self.debug = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback  # TODO: implement safety_checks
        self.ctx = ctx
        self.stream = stream
        self.bridge = bridge
        self.begin = True

        if computer:
            dimensions = computer.dimensions
            self.tools += [
                {
                    "type": "computer-preview",
                    "display_width": dimensions[0],
                    "display_height": dimensions[1],
                    "environment": computer.environment,
                },
            ]

    def debug_print(self, *args):
        """
        Print debug information if debug mode is enabled.

        :param args: Variable length argument list to print debug information.
        """
        if self.debug:
            pp(*args)

    def handle_item(self, item: dict) -> list:
        """
        Handle each item; may cause a computer action + screenshot.

        :param item: The item to handle, which can be a message, function call, or computer call.
        :return: A list of new items to be processed.
        """
        if self.bridge.stopped():
            if self.bridge.on_stop:
                self.bridge.on_stop(self.ctx)
            return []

        self.ctx.stream = ""

        if item["type"] == "message":
            if self.debug:
                print(item["content"][0]["text"])

            if self.stream:
                self.ctx.stream = item["content"][0]["text"]
                self.bridge.on_step(self.ctx, self.begin)

        if item["type"] == "function_call":
            name, args = item["name"], json.loads(item["arguments"])
            if self.debug:
                print(f"{name}({args})")

            if hasattr(self.computer, name):  # if function exists on computer, call it
                method = getattr(self.computer, name)
                method(**args)

            return [
                {
                    "type": "function_call_output",
                    "call_id": item["call_id"],
                    "output": "success",  # hard-coded output for demo
                }
            ]

        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.debug:
                print(f"{action_type}({action_args})")

            method = getattr(self.computer, action_type)
            method(**action_args)

            screenshot_base64 = self.computer.screenshot()
            pending_checks = item.get("pending_safety_checks", [])
            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            return [call_output]
        return []

    def run(
        self,
        input: list[dict],
        debug: bool = False
    ):
        """
        Run a full turn of the agent, processing input items and returning new items.

        :param input: a list of messages.
        :param debug: bool, whether to enable debug mode.
        :return: tuple of new items and response ID.
        """
        self.debug = debug
        new_items = []
        response_id = None

        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if new_items else True:

            # if kernel stopped then break the loop
            if self.bridge.stopped():
                if self.bridge.on_stop:
                    self.bridge.on_stop(self.ctx)
                break

            self.debug_print([sanitize_message(msg) for msg in input + new_items])

            response = create_response(
                model=self.model,
                input=input + new_items,
                tools=self.tools,
                truncation="auto",
            )
            self.debug_print(response)

            if "output" not in response and self.debug:
                print(response)
                self.bridge.on_error(str(response))
                break
            else:
                new_items += response["output"]
                for item in response["output"]:
                    new_items += self.handle_item(item)

            response_id = response.get("id")
            self.begin = False  # reset

        return new_items, response_id