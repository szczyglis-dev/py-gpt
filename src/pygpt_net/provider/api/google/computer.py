#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.09 00:30:00                  #
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
        """Map PyGPT's selected environment to the best enum supported by the installed SDK."""
        env = self.get_current_env()
        value = ""
        if isinstance(env, str):
            value = env.lower()
        elif isinstance(env, dict):
            value = str(env.get("value") or env.get("name") or env).lower()

        enum = gtypes.Environment
        # Newer Gemini Computer Use exposes a generic desktop environment. Prefer it
        # for host OS control; retain older OS-specific enum fallbacks for SDK compatibility.
        if any(token in value for token in ("desktop", "linux", "windows", "win", "mac")):
            desktop = getattr(enum, "ENVIRONMENT_DESKTOP", None)
            if desktop is not None:
                return desktop
        if "mac" in value and hasattr(enum, "ENVIRONMENT_MAC"):
            return enum.ENVIRONMENT_MAC
        if ("windows" in value or "win" in value) and hasattr(enum, "ENVIRONMENT_WINDOWS"):
            return enum.ENVIRONMENT_WINDOWS
        if "linux" in value and hasattr(enum, "ENVIRONMENT_LINUX"):
            return enum.ENVIRONMENT_LINUX
        return enum.ENVIRONMENT_BROWSER

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
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
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

    @staticmethod
    def _safety_value(value) -> str:
        if value is None:
            return ""
        raw = getattr(value, "value", value)
        text = str(raw).strip().lower()
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        return text

    def _record_safety_decision(self, ctx: CtxItem, name: str, args: dict) -> None:
        """Record Gemini Computer Use safety_decision metadata for the shared confirmation gate."""
        if not args:
            return
        try:
            raw = args.get("safety_decision")
        except Exception:
            raw = None
        if raw is None:
            return

        if isinstance(raw, dict) or hasattr(raw, "get"):
            try:
                decision = raw.get("decision")
                explanation = raw.get("explanation")
            except Exception:
                decision = getattr(raw, "decision", None)
                explanation = getattr(raw, "explanation", None)
        else:
            decision = getattr(raw, "decision", None)
            explanation = getattr(raw, "explanation", None)

        decision_value = self._safety_value(decision)
        if decision_value != "require_confirmation":
            return

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        decisions = ctx.extra.setdefault("computer_safety_decisions", [])
        item = {
            "provider": "google",
            "function": str(name or ""),
            "decision": decision_value,
            "explanation": str(explanation or "").strip(),
        }
        if item not in decisions:
            decisions.append(item)

    @staticmethod
    def _normalize_key_list(value) -> list:
        if isinstance(value, str):
            return [part.strip() for part in value.replace("+", " ").split() if part.strip()]
        return list(value or [])

    def _map_function(self, name: str, args: dict) -> Tuple[Optional[str], dict]:
        """Map a Gemini Computer Use function to PyGPT's canonical executor contract."""
        name = str(name or "")
        p = dict(args or {})
        coord = {"coordinate_space": "normalized"}

        if name in {"click", "double_click", "triple_click", "middle_click", "right_click"}:
            count = 1
            button = "left"
            if name == "double_click": count = 2
            elif name == "triple_click": count = 3
            elif name == "middle_click": button = "middle"
            elif name == "right_click": button = "right"
            return "mouse_click", {**coord, "x": p.get("x"), "y": p.get("y"),
                                   "button": button, "num_clicks": count}
        if name in {"move", "hover_at"}:
            return "mouse_move", {**coord, "x": p.get("x"), "y": p.get("y")}
        if name == "mouse_down":
            return "mouse_down", {**coord, "x": p.get("x"), "y": p.get("y"),
                                  "button": p.get("button", "left")}
        if name == "mouse_up":
            return "mouse_up", {**coord, "x": p.get("x"), "y": p.get("y"),
                                "button": p.get("button", "left")}
        if name in {"type", "keyboard_type"}:
            return "keyboard_type", {"text": p.get("text", ""),
                                     "press_enter": bool(p.get("press_enter", False))}
        if name in {"press_key", "keyboard_key"}:
            return "keyboard_key", {"key": p.get("key", p.get("text", ""))}
        if name == "key_down":
            return "key_down", {"key": p.get("key", p.get("text", ""))}
        if name == "key_up":
            return "key_up", {"key": p.get("key", p.get("text", ""))}
        if name in {"hotkey", "key_combination", "keypress"}:
            return "keyboard_keys", {"keys": self._normalize_key_list(p.get("keys", p.get("key", [])))}
        if name in {"take_screenshot", "screenshot"}:
            return "get_screenshot", {}
        if name in {"wait", "wait_5_seconds"}:
            return "wait", {"seconds": p.get("seconds", 5 if name == "wait_5_seconds" else 1)}
        if name == "long_press":
            return "long_press", {**coord, "x": p.get("x"), "y": p.get("y"),
                                  "duration": p.get("duration", p.get("duration_seconds", 0.5)),
                                  "button": p.get("button", "left")}
        if name in {"drag_and_drop", "drag"}:
            if p.get("path"):
                path = p.get("path")
            else:
                sx = p.get("start_x", p.get("x")); sy = p.get("start_y", p.get("y"))
                ex = p.get("end_x", p.get("destination_x", p.get("dx")))
                ey = p.get("end_y", p.get("destination_y", p.get("dy")))
                path = [{"x": sx, "y": sy}, {"x": ex, "y": ey}]
            return "mouse_drag", {**coord, "path": path}
        if name in {"scroll", "scroll_at", "scroll_document"}:
            direction = str(p.get("direction", "") or "").lower()
            magnitude = int(p.get("magnitude_in_pixels", p.get("magnitude", 0)) or 0)
            dx = int(p.get("scroll_x", p.get("dx", 0)) or 0)
            dy = int(p.get("scroll_y", p.get("dy", 0)) or 0)
            if direction and magnitude:
                if direction == "down": dy = magnitude
                elif direction == "up": dy = -magnitude
                elif direction == "right": dx = magnitude
                elif direction == "left": dx = -magnitude
            out = {**coord, "dx": dx, "dy": dy, "unit": "px", "scroll_mode": "viewport"}
            if p.get("x") is not None and p.get("y") is not None:
                out.update({"x": p.get("x"), "y": p.get("y")})
            return "mouse_scroll", out
        if name == "open_web_browser":
            return "open_web_browser", {"url": p.get("url", "")}
        if name in {"navigate", "go_back", "go_forward", "search"}:
            return name, {k: v for k, v in p.items() if k in {"url", "query"}}
        if name == "click_at":
            return "mouse_click", {**coord, "x": p.get("x"), "y": p.get("y"), "button": "left", "num_clicks": 1}
        if name == "type_text_at":
            # Keep this compound browser action for compatibility with Gemini 2.x schemas.
            return "type_text_at", {**coord, **p}
        return None, {}

    def handle_stream_chunk(self, ctx: CtxItem, chunk, tool_calls: list) -> Tuple[List, bool]:
        """
        Handle function_call parts (Gemini) and older action-shaped events.
        All functions are passed through unchanged to the worker.

        Returns: updated tool_calls and a boolean indicating if there were calls.
        """
        has_calls = False

        # Case A: Google SDK function_call parts (recommended)
        for fname, fargs, provider_call_id in self._iter_function_calls(chunk):
            if not fname:
                continue
            self._record_safety_decision(ctx, fname, fargs or {})
            # Keep Gemini's protocol id when the SDK supplies one. It is persisted
            # with the local task and echoed by Chat in the following FunctionResponse.
            id_ = str(provider_call_id or self._next_id())
            call_id = id_
            try:
                local_name, local_args = self._map_function(fname, fargs or {})
                if local_name:
                    self._append_call(tool_calls, id_, call_id, local_name, local_args)
                    has_calls = True
                else:
                    print(f"Gemini: unsupported Computer Use function '{fname}'")
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
        """Return (name, args, provider_call_id) tuples from Gemini responses/chunks."""
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
                                    call_id = getattr(fc, "id", None) or ""
                                    calls.append((name, args, call_id))
            else:
                if isinstance(resp, dict):
                    content = resp.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "function_call" in part:
                            fc = part["function_call"]
                            calls.append((fc.get("name"), fc.get("args", {}), fc.get("id", "")))
        except Exception as e:
            print(f"Gemini: failed to parse function_call: {e}")
        return calls

    def _pass_action(self, action) -> Tuple[Optional[str], dict]:
        """Convert an older action-shaped event through the same canonical mapper."""
        try:
            atype = getattr(action, "type", None)
            if not atype:
                return None, {}
            args = {}
            for attr in (
                    "x", "y", "button", "scroll_x", "scroll_y", "keys", "key",
                    "text", "path", "start_x", "start_y", "end_x", "end_y",
                    "direction", "magnitude", "magnitude_in_pixels", "seconds"):
                if hasattr(action, attr):
                    args[attr] = getattr(action, attr)
            return self._map_function(str(atype), args)
        except Exception as e:
            print(f"Gemini: pass_action error: {e}")
            return None, {}

