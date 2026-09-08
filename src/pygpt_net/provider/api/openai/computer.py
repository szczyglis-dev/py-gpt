#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 14:59:00                  #
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

    @staticmethod
    def _get(obj, key: str, default=None):
        """
        Read a field from either an SDK object or a raw dictionary.

        Responses streaming may expose Computer Use actions as plain dicts
        even when the surrounding response item is a typed SDK object.

        :param obj: source object or dictionary
        :param key: field name
        :param default: fallback value
        :return: field value
        """
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def get_current_env(self) -> Dict[str, Any]:
        """
        Get current computer environment

        :return: Dict[str, Any]
        """
        idx = self.window.ui.nodes["computer_env"].currentIndex()
        return self.window.ui.nodes["computer_env"].itemData(idx)

    def get_tool(self) -> dict:
        """
        Get the GA Computer Use tool definition.

        Display dimensions and environment were part of the retired
        ``computer_use_preview`` tool shape. The current Responses API
        discovers the screen state from the screenshots returned by the client.

        :return: dict
        """
        return {"type": "computer"}

    @staticmethod
    def get_actions(item) -> list:
        """
        Return ordered Computer Use actions from a response item.

        GA Computer Use returns a batched ``actions`` array. Keep a fallback
        for the legacy single ``action`` field so saved/mock response objects
        and compatible providers do not break during migration.

        :param item: computer_call response item
        :return: ordered list of actions
        """
        actions = Computer._get(item, "actions")
        if actions:
            return list(actions)
        action = Computer._get(item, "action")
        return [action] if action is not None else []

    def handle_actions(
            self,
            id: str,
            call_id: str,
            actions: list,
            tool_calls: list
    ) -> Tuple[List, bool]:
        """
        Convert an ordered batch of Computer Use actions into local tool calls.

        :param id: response item ID
        :param call_id: Computer Use call ID
        :param actions: ordered actions returned by the model
        :param tool_calls: destination tool-call list
        :return: tool calls and whether at least one action was converted
        """
        has_calls = False
        for action in actions or []:
            tool_calls, is_call = self.handle_action(
                id=id,
                call_id=call_id,
                action=action,
                tool_calls=tool_calls,
            )
            has_calls = has_calls or is_call
        return tool_calls, has_calls

    @staticmethod
    def store_pending_safety_checks(ctx: CtxItem, item):
        """
        Preserve legacy preview safety checks when present.

        GA Computer Use no longer uses the old pending-safety-check payload,
        but keeping this tolerant reader avoids regressions with stored/mock
        legacy response objects.

        :param ctx: context item
        :param item: computer_call response item
        """
        pending = Computer._get(item, "pending_safety_checks") or []
        if not pending:
            return
        ctx.extra["pending_safety_checks"] = []
        for check in pending:
            ctx.extra["pending_safety_checks"].append({
                "id": Computer._get(check, "id"),
                "code": Computer._get(check, "code"),
                "message": Computer._get(check, "message"),
            })

    def handle_stream_chunk(self, ctx: CtxItem, chunk, tool_calls: list) -> Tuple[List, bool]:
        """
        Handle stream chunk for computer use

        :param ctx: context item
        :param chunk: stream chunk
        :param tool_calls: list of tool calls
        :return: Tool calls and a boolean indicating if there are calls
        """
        has_calls = False

        item = self._get(chunk, "item")
        if item is not None and self._get(item, "type") == "computer_call":
            id = self._get(item, "id")
            call_id = self._get(item, "call_id")
            tool_calls, has_calls = self.handle_actions(
                id=id,
                call_id=call_id,
                actions=self.get_actions(item),
                tool_calls=tool_calls,
            )
            self.store_pending_safety_checks(ctx, item)
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

        action_type = self._get(action, "type")

        # mouse click
        if action_type == "click":
            button = self._get(action, "button", "left")
            x = self._get(action, "x")
            y = self._get(action, "y")
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
        elif action_type in ["double_click", "dblclick", "dbl_click"]:
            x = self._get(action, "x")
            y = self._get(action, "y")
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
        elif action_type == "move":
            x = self._get(action, "x")
            y = self._get(action, "y")
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
        elif action_type == "screenshot":
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
        elif action_type == "type":
            text = self._get(action, "text", "")
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
        elif action_type == "keypress":
            keys = self._get(action, "keys", [])
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
        elif action_type == "scroll":
            x = self._get(action, "x")
            y = self._get(action, "y")
            dx = self._get(action, "scroll_x", 0)
            dy = self._get(action, "scroll_y", 0)
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
        elif action_type == "wait":
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

        elif action_type == "drag":
            path = self._get(action, "path", [])
            if len(path) < 2:
                print("Invalid drag action path")
                return tool_calls, False
            x = self._get(path[0], "x")
            y = self._get(path[0], "y")
            dx = self._get(path[1], "x")
            dy = self._get(path[1], "y")
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
            print(f"Unrecognized action type: {action_type}")

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
        action_type = self._get(action, "type")
        try:
            match action_type:
                case "click":
                    has_calls = True
                    x, y = self._get(action, "x"), self._get(action, "y")
                    button = self._get(action, "button", "left")
                    print(f"Action: click at ({x}, {y}) with button '{button}'")
                    # Not handling things like middle click, etc.
                    if button != "left" and button != "right":
                        button = "left"
                    page.mouse.click(x, y, button=button)

                case "scroll":
                    has_calls = True
                    x, y = self._get(action, "x"), self._get(action, "y")
                    scroll_x, scroll_y = self._get(action, "scroll_x", 0), self._get(action, "scroll_y", 0)
                    print(f"Action: scroll at ({x}, {y}) with offsets (scroll_x={scroll_x}, scroll_y={scroll_y})")
                    page.mouse.move(x, y)
                    page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

                case "keypress":
                    has_calls = True
                    keys = self._get(action, "keys", [])
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
                    text = self._get(action, "text", "")
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