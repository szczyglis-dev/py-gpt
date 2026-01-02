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

import json
import time
from typing import Dict, Any, List, Tuple

from pygpt_net.item.ctx import CtxItem


class Computer:
    def __init__(self, window=None):
        """
        Computer use mode

        :param window: Window instance
        """
        self.window = window

    def get_current_env(self) -> Dict[str, Any]:
        """
        Get current computer environment

        :return: Dict[str, Any]
        """
        idx = self.window.ui.nodes["computer_env"].currentIndex()
        return self.window.ui.nodes["computer_env"].itemData(idx)

    def get_tool(self) -> dict:
        """
        Get Computer use tool
        :return: dict
        """
        is_sandbox = bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))
        env = self.get_current_env()
        screen = self.window.app.primaryScreen()
        size = screen.size()
        screen_x = size.width()
        screen_y = size.height()

        # if sandbox, get resolution from plugin settings (Playwright viewport)
        if is_sandbox:
            try:
                screen_x = int(self.window.core.plugins.get_option("cmd_mouse_control", "sandbox_viewport_w"))
                screen_y = int(self.window.core.plugins.get_option("cmd_mouse_control", "sandbox_viewport_h"))
            except Exception:
                pass
        return {
            "type": "computer_use_preview",
            "display_width": screen_x,
            "display_height": screen_y,
            "environment": env,  # "browser", "mac", "windows", "linux"
        }

    def handle_stream_chunk(self, ctx: CtxItem, chunk, tool_calls: list) -> Tuple[List, bool]:
        """
        Handle stream chunk for computer use

        :param ctx: context item
        :param chunk: stream chunk
        :param tool_calls: list of tool calls
        :return: Tool calls and a boolean indicating if there are calls
        """
        has_calls = False

        if chunk.item.type == "computer_call":
            id = chunk.item.id
            call_id = chunk.item.call_id
            action = chunk.item.action
            tool_calls, has_calls = self.handle_action(
                id=id,
                call_id=call_id,
                action=action,
                tool_calls=tool_calls,
            )
            if chunk.item.pending_safety_checks:
                ctx.extra["pending_safety_checks"] = []
                for item in chunk.item.pending_safety_checks:
                    check = {
                        "id": item.id,
                        "code": item.code,
                        "message": item.message,
                    }
                    ctx.extra["pending_safety_checks"].append(check)
        return tool_calls, has_calls

    def handle_action(
            self,
            id: str,
            call_id: str,
            action,
            tool_calls: list
    ) -> Tuple[List, bool]:
        """
        Handle action for computer use

        :param id: unique identifier for the action
        :param call_id: unique identifier for the call
        :param tool_calls: list of tool calls
        :return: Tool calls and a boolean indicating if there are calls
        """
        has_calls = False

        # mouse click
        if action.type == "click":
            button = action.button
            x = action.x
            y = action.y
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "mouse_move",
                    "arguments": json.dumps({
                        "x": x,
                        "y": y,
                        "click": button,
                        "num_clicks": 1,
                    })
                }
            })
            has_calls = True

        # mouse double click
        elif action.type in ["double_click", "dblclick", "dbl_click"]:
            x = action.x
            y = action.y
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "mouse_move",
                    "arguments": json.dumps({
                        "x": x,
                        "y": y,
                        "click": "left",  # default to left click
                        "num_clicks": 2,
                    })
                }
            })
            has_calls = True

        # mouse move
        elif action.type == "move":
            x = action.x
            y = action.y
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "mouse_move",
                    "arguments": json.dumps({
                        "x": x,
                        "y": y,
                    })
                }
            })
            has_calls = True

        # get screenshot
        elif action.type == "screenshot":
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "get_screenshot",
                    "arguments": "{}"
                }
            })
            has_calls = True

        # keyboard type
        elif action.type == "type":
            text = action.text
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "keyboard_type",
                    "arguments": json.dumps({
                        "text": text,
                    })
                }
            })
            has_calls = True

        # keyboard keys
        elif action.type == "keypress":
            keys = action.keys
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "keyboard_keys",
                    "arguments": json.dumps({
                        "keys": keys, # sequence in list
                    })
                }
            })
            has_calls = True

        # mouse scroll
        elif action.type == "scroll":
            x = action.x
            y = action.y
            dx = action.scroll_x
            dy = action.scroll_y
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "mouse_scroll",
                    "arguments": json.dumps({
                        "x": x,
                        "y": y,
                        "dx": dx,
                        "dy": -dy,  # invert scroll direction
                        "unit": "px",
                    })
                }
            })
            has_calls = True

        # wait for a while
        elif action.type == "wait":
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "wait",
                    "arguments": "{}"
                }
            })
            has_calls = True

        elif action.type == "drag":
            x = action.path[0].x
            y = action.path[0].y
            dx = action.path[1].x
            dy = action.path[1].y
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "mouse_drag",
                    "arguments": json.dumps({
                        "x": x,
                        "y": y,
                        "dx": dx,
                        "dy": dy,
                    })
                }
            })
            has_calls = True
        else:
            # append empty to store tool call
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "wait",
                    "arguments": "{}"
                }
            })
            has_calls = True
            print(f"Unrecognized action type: {action.type}")

        return tool_calls, has_calls

    def handle_browser(self,
            id: str,
            call_id: str,
            action,
            tool_calls: list,
            page):
        """
        Given a computer action (e.g., click, double_click, scroll, etc.),
        execute the corresponding operation on the Playwright page.

        :param id: Unique identifier for the action
        :param call_id: Unique identifier for the call
        :param action: The action to be performed
        :param tool_calls: List to store tool calls
        :param page: The Playwright page object to interact with
        :return: Updated tool_calls list
        """
        has_calls = False
        action_type = action.type
        try:
            match action_type:
                case "click":
                    has_calls = True
                    x, y = action.x, action.y
                    button = action.button
                    print(f"Action: click at ({x}, {y}) with button '{button}'")
                    # Not handling things like middle click, etc.
                    if button != "left" and button != "right":
                        button = "left"
                    page.mouse.click(x, y, button=button)

                case "scroll":
                    has_calls = True
                    x, y = action.x, action.y
                    scroll_x, scroll_y = action.scroll_x, action.scroll_y
                    print(f"Action: scroll at ({x}, {y}) with offsets (scroll_x={scroll_x}, scroll_y={scroll_y})")
                    page.mouse.move(x, y)
                    page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

                case "keypress":
                    has_calls = True
                    keys = action.keys
                    for k in keys:
                        print(f"Action: keypress '{k}'")
                        # A simple mapping for common keys; expand as needed.
                        if k.lower() == "enter":
                            page.keyboard.press("Enter")
                        elif k.lower() == "space":
                            page.keyboard.press(" ")
                        else:
                            page.keyboard.press(k)

                case "type":
                    has_calls = True
                    text = action.text
                    print(f"Action: type text: {text}")
                    page.keyboard.type(text)

                case "wait":
                    has_calls = True
                    print(f"Action: wait")
                    time.sleep(2)

                case "screenshot":
                    has_calls = True
                    # Nothing to do as screenshot is taken at each turn
                    print(f"Action: screenshot")

                # Handle other actions here
                case _:
                    print(f"Unrecognized action: {action}")

        except Exception as e:
            print(f"Error handling action {action}: {e}")

        if has_calls:
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": "get_screenshot",
                    "arguments": "{}"
                }
            })