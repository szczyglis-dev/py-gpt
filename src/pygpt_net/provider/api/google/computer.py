#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.01.02 02:00:00                  #
# ================================================== #

import json
import time
from typing import Dict, Any, List, Tuple, Optional

from google.genai import types as gtypes
from pygpt_net.item.ctx import CtxItem


class Computer:
    def __init__(self, window=None):
        """
        Google Gemini Computer Use adapter

        This adapter passes Google Gemini function calls and action events
        directly to the plugin worker without translating names to legacy
        commands. The workers (host and sandbox) implement the full set
        of functions and handle any coordinate conversions themselves.
        """
        self.window = window
        self._seq = 0

    # --------------- Tool spec --------------- #

    def get_current_env(self) -> Dict[str, Any]:
        idx = self.window.ui.nodes["computer_env"].currentIndex()
        return self.window.ui.nodes["computer_env"].itemData(idx)

    def _map_env(self) -> gtypes.Environment:
        return gtypes.Environment.ENVIRONMENT_BROWSER
        env = self.get_current_env()
        val = ""
        if isinstance(env, str):
            val = env.lower()
        elif isinstance(env, dict):
            val = str(env.get("value") or env.get("name") or env).lower()
        if "mac" in val:
            return gtypes.Environment.ENVIRONMENT_MAC
        if "windows" in val or "win" in val:
            return gtypes.Environment.ENVIRONMENT_WINDOWS
        if "linux" in val:
            return gtypes.Environment.ENVIRONMENT_LINUX
        return gtypes.Environment.ENVIRONMENT_BROWSER

    def get_tool(self) -> gtypes.Tool:
        return gtypes.Tool(
            computer_use=gtypes.ComputerUse(
                environment=self._map_env(),
            )
        )

    # --------------- Streaming handling --------------- #

    def _next_id(self) -> str:
        self._seq += 1
        return f"gc-{int(time.time()*1000)}-{self._seq}"

    def _append_call(self, tool_calls: list, id_: str, call_id: str, name: str, args: dict) -> None:
        tool_calls.append({
            "id": id_,
            "call_id": call_id,
            "type": "computer_call",
            "function": {
                "name": name,
                "arguments": json.dumps(args or {}),
            }
        })

    def _append_screenshot(self, tool_calls: list, id_: str, call_id: str) -> None:
        self._append_call(tool_calls, id_, call_id, "get_screenshot", {})

    def _record_pending_checks(self, ctx: CtxItem, pending: Optional[list]) -> None:
        if not pending:
            return
        ctx.extra["pending_safety_checks"] = []
        for item in pending:
            try:
                ctx.extra["pending_safety_checks"].append({
                    "id": getattr(item, "id", None),
                    "code": getattr(item, "code", None),
                    "message": getattr(item, "message", None),
                })
            except Exception:
                pass

    def handle_stream_chunk(self, ctx: CtxItem, chunk, tool_calls: list) -> Tuple[List, bool]:
        """
        Handle function_call parts (Gemini) and older action-shaped events.
        All functions are passed through unchanged to the worker.

        Returns: updated tool_calls and a boolean indicating if there were calls.
        """
        has_calls = False

        # Case A: Google SDK function_call parts (recommended)
        for fname, fargs in self._iter_function_calls(chunk):
            if not fname:
                continue
            id_ = self._next_id()
            call_id = id_
            try:
                self._append_call(tool_calls, id_, call_id, fname, fargs or {})
                has_calls = True
            except Exception as e:
                print(f"Gemini pass-through error for function '{fname}': {e}")

        # Case B: Older/OpenAI-shaped events embedded as chunk.item.action
        try:
            item = getattr(chunk, "item", None)
            if item and getattr(item, "type", "") == "computer_call":
                id_ = getattr(item, "id", None) or self._next_id()
                call_id = getattr(item, "call_id", None) or id_
                action = getattr(item, "action", None)
                if action:
                    name, args = self._pass_action(action)
                    if name:
                        self._append_call(tool_calls, id_, call_id, name, args)
                        has_calls = True
                # optional pending safety checks
                if getattr(item, "pending_safety_checks", None):
                    self._record_pending_checks(ctx, item.pending_safety_checks)
        except Exception as e:
            print(f"Gemini action stream parse error: {e}")

        return tool_calls, has_calls

    # --------------- Parsers --------------- #

    def _iter_function_calls(self, resp) -> List[tuple]:
        calls = []
        try:
            candidates = getattr(resp, "candidates", None)
            if candidates:
                for cand in candidates:
                    content = getattr(cand, "content", None)
                    if content:
                        parts = getattr(content, "parts", None)
                        if parts:
                            for part in parts:
                                fc = getattr(part, "function_call", None)
                                if fc:
                                    name = getattr(fc, "name", None)
                                    args = getattr(fc, "args", {}) or {}
                                    calls.append((name, args))
            else:
                if isinstance(resp, dict):
                    content = resp.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "function_call" in part:
                            fc = part["function_call"]
                            calls.append((fc.get("name"), fc.get("args", {})))
        except Exception as e:
            print(f"Gemini: failed to parse function_call: {e}")
        return calls

    def _pass_action(self, action) -> Tuple[Optional[str], dict]:
        """
        Convert old-style action object into a direct function call name + args,
        without changing the semantic names (workers handle details).
        """
        try:
            atype = getattr(action, "type", None)
            if not atype:
                return None, {}
            atype = str(atype)

            # Build args by introspection; workers know how to interpret them
            args = {}
            for attr in ("x", "y", "button", "scroll_x", "scroll_y", "keys", "text", "path"):
                if hasattr(action, attr):
                    args[attr] = getattr(action, attr)

            if atype == "double_click":
                args["num_clicks"] = 2

            return atype, args
        except Exception as e:
            print(f"Gemini: pass_action error: {e}")
            return None, {}