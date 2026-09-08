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
        """Map one OpenAI Computer Use action to the local canonical executor."""
        action_type = self._get(action, "type")
        common = {"coordinate_space": "screen"}
        keys = self._get(action, "keys", []) or []

        def append(name: str, args: dict = None):
            payload = dict(common)
            payload.update(args or {})
            tool_calls.append({
                "id": id,
                "call_id": call_id,
                "type": "computer_call",
                "function": {
                    "name": name,
                    "arguments": json.dumps(payload),
                },
            })

        if action_type == "click":
            append("mouse_click", {
                "x": self._get(action, "x"),
                "y": self._get(action, "y"),
                "button": self._get(action, "button", "left"),
                "num_clicks": 1,
                "keys": keys,
            })
        elif action_type in {"double_click", "dblclick", "dbl_click"}:
            append("mouse_click", {
                "x": self._get(action, "x"),
                "y": self._get(action, "y"),
                "button": "left",
                "num_clicks": 2,
                "keys": keys,
            })
        elif action_type == "move":
            append("mouse_move", {
                "x": self._get(action, "x"),
                "y": self._get(action, "y"),
                "keys": keys,
            })
        elif action_type == "screenshot":
            append("get_screenshot", {})
        elif action_type == "type":
            append("keyboard_type", {"text": self._get(action, "text", "")})
        elif action_type == "keypress":
            append("keyboard_keys", {"keys": self._get(action, "keys", []) or []})
        elif action_type == "scroll":
            append("mouse_scroll", {
                "x": self._get(action, "x"),
                "y": self._get(action, "y"),
                "dx": self._get(action, "scroll_x", 0),
                "dy": self._get(action, "scroll_y", 0),
                "unit": "px",
                "scroll_mode": "viewport",
                "keys": keys,
            })
        elif action_type == "wait":
            append("wait", {})
        elif action_type == "drag":
            path = self._get(action, "path", []) or []
            if len(path) < 2:
                print("Invalid drag action path")
                return tool_calls, False
            append("mouse_drag", {
                "path": [
                    {"x": self._get(point, "x"), "y": self._get(point, "y")}
                    for point in path
                ],
                "keys": keys,
            })
        else:
            # Preserve the call/continuation rather than dropping an unknown action.
            append("wait", {})
            print(f"Unrecognized action type: {action_type}")

        return tool_calls, True

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