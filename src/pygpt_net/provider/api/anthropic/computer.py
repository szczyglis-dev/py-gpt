#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from pygpt_net.item.ctx import CtxItem


class Computer:
    """
    Anthropic Computer Use adapter.

    Responsibilities:
    - Provide Anthropic Computer Use tool spec (messages.create tools[]).
    - Rewrite Anthropic computer tool_use payloads into app-compatible tool calls
      for the Mouse & Keyboard plugin (same final shape as OpenAI/Google adapters).
    - Handle both content_block_delta.input_json_delta and top-level input_json_delta
      variants produced by Anthropic Beta streaming.
    """

    COMPUTER_TOOL_NAMES = {
        "computer",
        "computer.use",
        "anthropic/computer",
        "computer_use",
        "computer-use",
    }

    # Known plugin command names (Worker supports these).
    # Used to normalize arguments when upstream sends Anthropic-shaped payloads as direct function calls.
    PLUGIN_COMMAND_NAMES = {
        "open_web_browser",
        "get_mouse_position",
        "mouse_move",
        "mouse_drag",
        "mouse_click",
        "mouse_scroll",
        "get_screenshot",
        "keyboard_key",
        "keyboard_keys",
        "keyboard_type",
        "wait",
        # host-native extras
        "wait_5_seconds",
        "go_back",
        "go_forward",
        "search",
        "navigate",
        "click_at",
        "hover_at",
        "type_text_at",
        "key_combination",
        "scroll_document",
        "scroll_at",
        "drag_and_drop",
        # action-style
        "click",
        "double_click",
        "move",
        "type",
        "keypress",
        "scroll",
        "drag",
    }

    # Action name synonyms that may appear in Anthropic payloads -> plugin command names
    ACTION_SYNONYMS = {
        "hover": "mouse_move",
        "move": "mouse_move",
        "mouse_move": "mouse_move",

        "click": "mouse_click",
        "left_click": "mouse_click",
        "right_click": "mouse_click",
        "double_click": "mouse_click",

        "scroll": "mouse_scroll",
        "mouse_scroll": "mouse_scroll",

        "drag": "mouse_drag",
        "drag_and_drop": "mouse_drag",
        "mouse_drag": "mouse_drag",

        "type": "keyboard_type",
        "input": "keyboard_type",
        "keyboard_type": "keyboard_type",

        "keypress": "keyboard_keys",
        "key": "keyboard_keys",
        "keys": "keyboard_keys",
        "key_combination": "key_combination",

        "screenshot": "get_screenshot",
        "get_screenshot": "get_screenshot",

        "wait": "wait",
        "sleep": "wait",
    }

    KEY_MODIFIERS = {"ctrl", "control", "alt", "shift", "cmd", "super", "start"}

    def __init__(self, window=None):
        """
        :param window: Window instance
        """
        self.window = window

    # --------------- Tool spec --------------- #

    def get_current_env(self) -> Dict[str, Any]:
        idx = self.window.ui.nodes["computer_env"].currentIndex()
        return self.window.ui.nodes["computer_env"].itemData(idx)

    def get_tool(self) -> dict:
        is_sandbox = bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))
        screen_w, screen_h = self._resolve_display_size(is_sandbox=is_sandbox)
        tool_type = str(self.window.core.config.get("remote_tools.anthropic.computer.type", "computer_20250124")).strip() or "computer_20250124"
        return {
            "name": "computer",
            "type": tool_type,
            "display_width_px": int(screen_w),
            "display_height_px": int(screen_h),
        }

    def _resolve_display_size(self, is_sandbox: bool) -> Tuple[int, int]:
        screen_w = screen_h = 0
        try:
            screen = self.window.app.primaryScreen()
            size = screen.size()
            screen_w = int(size.width())
            screen_h = int(size.height())
        except Exception:
            screen_w, screen_h = 1440, 900

        if is_sandbox:
            try:
                vw = int(self.window.core.plugins.get_option("cmd_mouse_control", "sandbox_viewport_w"))
                vh = int(self.window.core.plugins.get_option("cmd_mouse_control", "sandbox_viewport_h"))
                if vw > 0 and vh > 0:
                    screen_w, screen_h = vw, vh
            except Exception:
                pass

        return screen_w, screen_h

    # --------------- Streaming handling --------------- #

    def handle_stream_chunk(self, ctx: CtxItem, chunk, tool_calls: list) -> Tuple[List, bool]:
        """
        Convert Computer Use 'tool_use' streaming events into plugin tool calls.
        Supports:
          - content_block_delta/input_json_delta
          - top-level input_json_delta
        """
        has_calls = False
        etype = str(getattr(chunk, "type", "") or "")

        cmem = self._ensure_ctx_memory(ctx)

        if etype == "content_block_start":
            cb = getattr(chunk, "content_block", None)
            if cb and getattr(cb, "type", "") == "tool_use":
                name = str(getattr(cb, "name", "") or "")
                if name in self.COMPUTER_TOOL_NAMES:
                    idx = str(getattr(chunk, "index", 0) or 0)
                    tid = str(getattr(cb, "id", "") or self._gen_id(prefix="ac"))
                    cmem["index_to_id"][idx] = tid
                    cmem["buffers"].setdefault(tid, "")
                    cmem["active_ids"].append(tid)

        elif etype == "input_json_delta":
            pj = getattr(chunk, "partial_json", "") or ""
            if cmem["active_ids"]:
                tid = cmem["active_ids"][-1]
                cmem["buffers"][tid] = cmem["buffers"].get(tid, "") + pj

        elif etype == "content_block_delta":
            delta = getattr(chunk, "delta", None)
            if delta and getattr(delta, "type", "") == "input_json_delta":
                idx = str(getattr(chunk, "index", 0) or 0)
                tid = cmem["index_to_id"].get(idx)
                if tid:
                    pj = getattr(delta, "partial_json", "") or ""
                    cmem["buffers"][tid] = cmem["buffers"].get(tid, "") + pj

        elif etype == "content_block_stop":
            idx = str(getattr(chunk, "index", 0) or 0)
            tid = cmem["index_to_id"].pop(idx, None)
            if not tid and cmem["active_ids"]:
                tid = cmem["active_ids"].pop()
            elif tid and cmem["active_ids"]:
                if cmem["active_ids"] and cmem["active_ids"][-1] == tid:
                    cmem["active_ids"].pop()
                else:
                    try:
                        cmem["active_ids"].remove(tid)
                    except ValueError:
                        pass

            if tid:
                payload = self._safe_json_loads(cmem["buffers"].pop(tid, ""))
                if payload is not None:
                    try:
                        if not isinstance(ctx.extra, dict):
                            ctx.extra = {}
                        tu_list = ctx.extra.get("anthropic_tool_uses")
                        if not isinstance(tu_list, list):
                            tu_list = []
                        tu_list.append({"id": tid, "name": "computer", "input": payload})
                        ctx.extra["anthropic_tool_uses"] = tu_list
                        self.window.core.ctx.update_item(ctx)
                    except Exception:
                        pass

                    mapped = self._payload_to_tool_calls(tid, tid, payload)
                    if mapped:
                        tool_calls.extend(mapped)
                        has_calls = True

        elif etype == "message_stop":
            while cmem["active_ids"]:
                tid = cmem["active_ids"].pop()
                payload = self._safe_json_loads(cmem["buffers"].pop(tid, ""))
                if payload is None:
                    continue
                try:
                    if not isinstance(ctx.extra, dict):
                        ctx.extra = {}
                    tu_list = ctx.extra.get("anthropic_tool_uses")
                    if not isinstance(tu_list, list):
                        tu_list = []
                    tu_list.append({"id": tid, "name": "computer", "input": payload})
                    ctx.extra["anthropic_tool_uses"] = tu_list
                    self.window.core.ctx.update_item(ctx)
                except Exception:
                    pass
                mapped = self._payload_to_tool_calls(tid, tid, payload)
                if mapped:
                    tool_calls.extend(mapped)
                    has_calls = True

        return tool_calls, has_calls

    # --------------- Public normalization for function tools --------------- #

    def normalize_function_args_json(self, name: str, args_json: Optional[str]) -> Optional[str]:
        """
        Normalize function-call arguments (client tools) to plugin shape.
        Accepts JSON string, returns JSON string. Returns None on failure.
        """
        if args_json is None:
            return None
        try:
            data = json.loads(args_json)
        except Exception:
            return None

        target_name, coerced = self._retarget_function_name_and_args(name, data if isinstance(data, dict) else {})
        norm = self._normalize_params_for_plugin(target_name, coerced)
        norm = self._filter_args_for_plugin(target_name, norm)
        try:
            return json.dumps(norm, ensure_ascii=False)
        except Exception:
            return None

    # --------------- Non-stream helpers --------------- #

    def rewrite_tool_calls(self, tool_calls: List[dict]) -> List[dict]:
        """
        Rewrites:
        - tool_use(computer) payloads into a sequence of plugin tool calls
        - direct function calls that already use plugin commands but carry Anthropic-style args
          (e.g., coordinate/action) into plugin-ready args
        - action-name synonyms (e.g., left_click, hover) into canonical plugin commands

        Important: this method mutates the incoming items IN-PLACE so that even if caller
        ignores the return value and continues using the original list/reference, the
        rewritten arguments and names are preserved (prevents leaking 'action'/'coordinate').
        """
        out: List[dict] = []
        for i, tc in enumerate(tool_calls or []):
            try:
                f = tc.get("function") or {}
                name = str(f.get("name", "") or "")
                args_raw = f.get("arguments", {})
                args = self._safe_json_loads(args_raw) if isinstance(args_raw, str) else args_raw

                # Case 1: Anthropic "computer" tool_use payload -> expand to sequence of plugin calls
                if name in self.COMPUTER_TOOL_NAMES and isinstance(args, (dict, list)):
                    calls = self._payload_to_tool_calls(tc.get("id") or self._gen_id(),
                                                        tc.get("call_id") or tc.get("id") or self._gen_id(),
                                                        args)
                    if calls:
                        out.extend(calls)
                        continue
                    else:
                        out.append(tc)
                        continue

                # Case 2: Direct function calls -> normalize and FILTER, then mutate in place
                if isinstance(args, dict):
                    target_name, coerced = self._retarget_function_name_and_args(name, args)
                    norm = self._normalize_params_for_plugin(target_name, coerced)
                    norm = self._filter_args_for_plugin(target_name, norm)
                    pruned = self._prune_none(norm)

                    f["name"] = target_name
                    f["arguments"] = json.dumps(pruned, ensure_ascii=False)
                    tc["function"] = f

                    # Mutate the original reference inside the incoming list as well
                    tool_calls[i] = tc

                    out.append(tc)
                    continue

                # Fallback: leave unchanged
                out.append(tc)

            except Exception:
                out.append(tc)
        return out

    # --------------- Parsers / mappers --------------- #

    def _payload_to_tool_calls(self, id_: str, call_id: str, payload: Any) -> List[dict]:
        actions = self._extract_actions(payload)
        out: List[dict] = []
        for action in actions:
            mapped = self._map_single_action(action, id_, call_id)
            if mapped:
                out.append(mapped)
        return out

    def _extract_actions(self, payload: Any) -> List[dict]:
        if payload is None:
            return []

        def _coerce_action(obj: Any) -> Optional[dict]:
            if obj is None:
                return None
            if isinstance(obj, dict):
                # If Anthropic sends {"type": "...", ...}
                if "type" in obj:
                    return obj
                # If Anthropic sends {"action": "left_click", "coordinate": [...]}
                if "action" in obj and isinstance(obj["action"], str) and obj["action"]:
                    act = {"type": str(obj["action"]).strip().lower()}
                    for k in ("x", "y", "button", "dx", "dy", "scroll_x", "scroll_y", "keys", "key",
                              "text", "value", "path", "from", "to", "coordinate", "destination", "offset", "delta",
                              "seconds", "sec", "count", "num_clicks", "unit"):
                        if k in obj:
                            act[k] = obj[k]
                    return act
                # If Anthropic sends {"action": {...}}
                if "action" in obj and isinstance(obj["action"], dict):
                    return obj["action"]
                return None
            if isinstance(obj, str):
                s = obj.strip().lower()
                if s:
                    return {"type": s}
            return None

        if isinstance(payload, dict):
            if "actions" in payload and isinstance(payload["actions"], list):
                out = []
                for it in payload["actions"]:
                    coerced = _coerce_action(it)
                    if coerced:
                        out.append(coerced)
                return out
            coerced = _coerce_action(payload)
            return [coerced] if coerced else []

        if isinstance(payload, list):
            out = []
            for it in payload:
                coerced = _coerce_action(it)
                if coerced:
                    out.append(coerced)
            return out

        return []

    def _extract_xy(self, action: dict) -> Tuple[Optional[int], Optional[int]]:
        try:
            if "x" in action and "y" in action:
                return int(action["x"]), int(action["y"])
        except Exception:
            pass
        for key in ("coordinate", "coordinates", "position", "point", "center", "location", "loc", "pos"):
            val = action.get(key)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                try:
                    return int(val[0]), int(val[1])
                except Exception:
                    pass
            if isinstance(val, dict) and "x" in val and "y" in val:
                try:
                    return int(val["x"]), int(val["y"])
                except Exception:
                    pass
        return None, None

    def _extract_dxdy(self, action: dict) -> Tuple[int, int]:
        def as_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return default
        if "dx" in action or "dy" in action:
            return as_int(action.get("dx", 0)), as_int(action.get("dy", 0))
        if "scroll_x" in action or "scroll_y" in action:
            return as_int(action.get("scroll_x", 0)), as_int(action.get("scroll_y", 0))
        for key in ("offset", "delta", "scroll", "wheel"):
            val = action.get(key)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                return as_int(val[0]), as_int(val[1])
        return 0, 0

    def _parse_keys_list(self, keys_val: Any) -> List[str]:
        """
        Parse keys that can be string like 'ctrl+shift+p' or list of tokens.
        """
        if isinstance(keys_val, str):
            return [p.strip() for p in keys_val.replace("+", " ").split() if p.strip()]
        if isinstance(keys_val, list):
            out = []
            for k in keys_val:
                if isinstance(k, str):
                    out.extend([p.strip() for p in k.replace("+", " ").split() if p.strip()])
                else:
                    out.append(k)
            return out
        if keys_val is None:
            return []
        return [keys_val]

    def _map_single_action(self, action: dict, id_: str, call_id: str) -> Optional[dict]:
        atype = str(action.get("type", "") or action.get("action", "") or "").lower().strip()

        # Clicks
        if atype in {"click", "double_click", "dblclick", "dbl_click", "left_click", "right_click"}:
            x, y = self._extract_xy(action)
            button = action.get("button", "left")
            num_clicks = int(action.get("count", action.get("num_clicks", 2 if "double" in atype or "dbl" in atype else 1)))
            if atype == "right_click":
                button = "right"
            if atype == "left_click":
                button = "left"
                num_clicks = 1 if "num_clicks" not in action else num_clicks
            args = {"button": button, "num_clicks": num_clicks}
            if x is not None and y is not None:
                args["x"] = x
                args["y"] = y
            return self._build_call(id_, call_id, "mouse_click", args)

        # Move / Hover
        if atype in {"move", "mouse_move", "hover"}:
            x, y = self._extract_xy(action)
            args = {}
            if x is not None and y is not None:
                args["x"] = x
                args["y"] = y
            return self._build_call(id_, call_id, "mouse_move", args)

        # Scroll
        if atype in {"scroll", "mouse_scroll"}:
            x, y = self._extract_xy(action)
            dx, dy = self._extract_dxdy(action)
            args = {"dx": dx, "dy": dy, "unit": "px"}
            if x is not None and y is not None:
                args["x"] = x
                args["y"] = y
            return self._build_call(id_, call_id, "mouse_scroll", args)

        # Type text
        if atype in {"type", "keyboard_type", "input"}:
            text = str(action.get("text", "") or action.get("value", "") or "")
            return self._build_call(id_, call_id, "keyboard_type", {"text": text})

        # Keys / key-combos
        if atype in {"keypress", "key", "keys", "key_combination"}:
            keys = self._parse_keys_list(action.get("keys", action.get("key")))
            mods = [k for k in keys if isinstance(k, str) and k.lower() in self.KEY_MODIFIERS]
            if atype == "key_combination" or len(mods) > 1:
                return self._build_call(id_, call_id, "key_combination", {"keys": keys or []})
            return self._build_call(id_, call_id, "keyboard_keys", {"keys": keys or []})

        # Drag and drop
        if atype in {"drag", "drag_and_drop", "mouse_drag"}:
            path = action.get("path")
            if isinstance(path, list) and len(path) >= 2 and isinstance(path[0], dict) and isinstance(path[1], dict):
                try:
                    x0 = int(path[0].get("x")); y0 = int(path[0].get("y"))
                    x1 = int(path[1].get("x")); y1 = int(path[1].get("y"))
                    args = {"x": x0, "y": y0, "dx": x1, "dy": y1}
                except Exception:
                    x0, y0 = self._extract_xy(path[0])
                    x1, y1 = self._extract_xy(path[1])
                    args = {"x": int(x0 or 0), "y": int(y0 or 0), "dx": int(x1 or 0), "dy": int(y1 or 0)}
                return self._build_call(id_, call_id, "mouse_drag", args)
            fx, fy = None, None
            tx, ty = None, None
            f = action.get("from")
            t = action.get("to")
            if isinstance(f, dict) or isinstance(f, (list, tuple)):
                fx, fy = self._extract_xy({"coordinate": f} if not isinstance(f, dict) else f)
            if isinstance(t, dict) or isinstance(t, (list, tuple)):
                tx, ty = self._extract_xy({"coordinate": t} if not isinstance(t, dict) else t)
            if fx is None or fy is None:
                fx, fy = self._extract_xy(action)
            if tx is None or ty is None:
                for key in ("destination", "target", "end"):
                    val = action.get(key)
                    if val is not None:
                        tx, ty = self._extract_xy({"coordinate": val} if not isinstance(val, dict) else val)
                        break
            if tx is None or ty is None:
                tx, ty = self._extract_dxdy(action)
            args = {"x": int(fx or 0), "y": int(fy or 0), "dx": int(tx or 0), "dy": int(ty or 0)}
            return self._build_call(id_, call_id, "mouse_drag", args)

        # Screenshot
        if atype in {"screenshot", "get_screenshot"}:
            return self._build_call(id_, call_id, "get_screenshot", {})

        # Wait
        if atype in {"wait", "sleep"}:
            secs = int(action.get("seconds", action.get("sec", 2)))
            return self._build_call(id_, call_id, "wait", {"seconds": secs})

        # Fallback: short wait to avoid breaking flow
        return self._build_call(id_, call_id, "wait", {"seconds": 1})

    # --------------- Build / normalize calls --------------- #

    def _normalize_params_for_plugin(self, name: str, args: dict) -> dict:
        """
        Normalize arguments dict to match plugin Worker expectations.
        Conservative and side-effect-free; only maps/renames, does not invent values.
        """
        if not isinstance(args, dict):
            return {}
        out = dict(args)

        # coordinate -> x,y
        if "coordinate" in out and ("x" not in out or "y" not in out):
            coord = out.get("coordinate")
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    out["x"] = int(coord[0])
                    out["y"] = int(coord[1])
                except Exception:
                    pass
            elif isinstance(coord, dict) and "x" in coord and "y" in coord:
                out["x"] = coord.get("x")
                out["y"] = coord.get("y")
            out.pop("coordinate", None)

        # scroll_x/scroll_y -> dx,dy for scroll commands
        if name in ("mouse_scroll", "scroll"):
            if "scroll_x" in out and "dx" not in out:
                try:
                    out["dx"] = int(out.get("scroll_x", 0))
                except Exception:
                    pass
            if "scroll_y" in out and "dy" not in out:
                try:
                    out["dy"] = int(out.get("scroll_y", 0))
                except Exception:
                    pass
            if "unit" in out:
                unit = str(out.get("unit")).lower().strip()
                if unit in ("px", "pixel", "pixels"):
                    out["unit"] = "px"
                elif unit in ("step", "steps", "notch", "notches", "line", "lines"):
                    out["unit"] = "step"

        # offset / delta -> dx,dy
        if "dx" not in out or "dy" not in out:
            for k in ("offset", "delta"):
                val = out.get(k)
                if isinstance(val, (list, tuple)) and len(val) >= 2:
                    try:
                        out.setdefault("dx", int(val[0]))
                        out.setdefault("dy", int(val[1]))
                    except Exception:
                        pass

        # action -> button/num_clicks mapping
        act = str(out.get("action", "") or "").lower()
        if act:
            is_double = ("double" in act) or ("dbl" in act)
            if "right" in act:
                out["button"] = "right"
            else:
                out["button"] = out.get("button", "left")
            out["num_clicks"] = 2 if is_double else int(out.get("num_clicks", 1))
            out.pop("action", None)

        # click -> button (defensive)
        if name in ("mouse_click", "click") and "click" in out and "button" not in out:
            out["button"] = out.pop("click")

        # destination -> dx,dy for drag
        if name in ("mouse_drag", "drag"):
            dest = out.get("destination") or out.get("target") or out.get("end")
            if dest is not None and ("dx" not in out or "dy" not in out):
                if isinstance(dest, (list, tuple)) and len(dest) >= 2:
                    try:
                        out["dx"] = int(dest[0])
                        out["dy"] = int(dest[1])
                    except Exception:
                        pass
                elif isinstance(dest, dict) and "x" in dest and "y" in dest:
                    out["dx"] = dest.get("x")
                    out["dy"] = dest.get("y")
                out.pop("destination", None)
                out.pop("target", None)
                out.pop("end", None)

        # keys normalization
        if name in ("keyboard_keys", "key_combination"):
            if "keys" not in out and "key" in out:
                out["keys"] = [out.get("key")]
                out.pop("key", None)
            if isinstance(out.get("keys"), str):
                out["keys"] = [p.strip() for p in out["keys"].replace("+", " ").split() if p.strip()]

        # text normalization for type
        if name == "keyboard_type":
            if "text" not in out and "value" in out:
                out["text"] = out.get("value")
                out.pop("value", None)

        # ensure unit for scroll
        if name in ("mouse_scroll", "scroll"):
            if "unit" not in out:
                out["unit"] = "px"

        return out

    def _append_call(self, tool_calls: list, id_: str, call_id: str, name: str, args: dict) -> None:
        tool_calls.append(self._build_call(id_, call_id, name, args))

    def _build_call(self, id_: str, call_id: str, name: str, args: dict) -> dict:
        norm = self._normalize_params_for_plugin(name, args or {})
        norm = self._filter_args_for_plugin(name, norm)
        norm = self._prune_none(norm)
        if name != "get_screenshot":
            norm["no_screenshot"] = True
        return {
            "id": id_,
            "call_id": call_id,
            "type": "computer_call",
            "function": {
                "name": name,
                "arguments": json.dumps(norm, ensure_ascii=False),
            }
        }

    # --------------- Utils --------------- #

    def _retarget_function_name_and_args(self, name: str, args: dict) -> Tuple[str, dict]:
        """
        Convert action-style/synonym function names to canonical plugin command names and
        adjust defaults (e.g., left_click/right_click/double_click).
        """
        src = (name or "").strip().lower()
        target = self.ACTION_SYNONYMS.get(src, src)
        out = dict(args or {})

        # Click synonyms defaulting button/click count
        if src in ("left_click", "right_click"):
            out.setdefault("button", "left" if src == "left_click" else "right")
            out.setdefault("num_clicks", 1)
        elif src == "double_click":
            out.setdefault("button", "left")
            out.setdefault("num_clicks", 2)

        # coordinate -> x,y (defensive retarget)
        if "coordinate" in out and ("x" not in out or "y" not in out):
            coord = out.get("coordinate")
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    out["x"] = int(coord[0])
                    out["y"] = int(coord[1])
                except Exception:
                    pass
            elif isinstance(coord, dict) and "x" in coord and "y" in coord:
                out["x"] = coord.get("x")
                out["y"] = coord.get("y")

        return target, out

    def _filter_args_for_plugin(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strict allow-list per command to ensure no unsupported keys like "action" or "coordinate"
        are passed to Worker. Also performs a few defensive conversions (click->button, etc.).
        """
        allow: Dict[str, set] = {
            "mouse_move": {"x", "y", "click", "num_clicks"},
            "mouse_click": {"x", "y", "button", "num_clicks"},
            "mouse_scroll": {"x", "y", "dx", "dy", "unit"},
            "mouse_drag": {"x", "y", "dx", "dy"},
            "keyboard_key": {"key", "modifier"},
            "keyboard_keys": {"keys"},
            "keyboard_type": {"text", "modifier"},
            "open_web_browser": {"url", "no_screenshot"},
            "get_mouse_position": {"no_screenshot"},
            "get_screenshot": {"no_screenshot"},
            "wait": {"seconds", "no_screenshot"},
            # native extras
            "wait_5_seconds": set(),
            "go_back": set(),
            "go_forward": set(),
            "search": set(),
            "navigate": {"url"},
            "click_at": {"x", "y"},
            "hover_at": {"x", "y"},
            "type_text_at": {"x", "y", "text", "press_enter", "clear_before_typing"},
            "key_combination": {"keys"},
            "scroll_document": {"direction", "magnitude"},
            "scroll_at": {"direction", "magnitude", "x", "y"},
            "drag_and_drop": {"x", "y", "destination_x", "destination_y"},
            # action-style
            "click": {"x", "y", "button", "num_clicks"},
            "double_click": {"x", "y", "button", "num_clicks"},
            "move": {"x", "y"},
            "type": {"text"},
            "keypress": {"keys"},
            "scroll": {"x", "y", "dx", "dy", "unit"},
            "drag": {"x", "y", "dx", "dy", "path"},
        }
        res: Dict[str, Any] = {}

        # coordinate -> x,y (final defensive conversion)
        if "coordinate" in args and ("x" not in args or "y" not in args):
            coord = args.get("coordinate")
            if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    args["x"] = int(coord[0])
                    args["y"] = int(coord[1])
                except Exception:
                    pass
            elif isinstance(coord, dict) and "x" in coord and "y" in coord:
                args["x"] = coord.get("x")
                args["y"] = coord.get("y")

        # action -> button/num_clicks (final defensive conversion)
        if "action" in args and (name in ("mouse_click", "click", "mouse_move")):
            act = str(args.get("action") or "").lower()
            if "right" in act:
                args["button"] = "right"
            else:
                args["button"] = args.get("button", "left")
            args["num_clicks"] = 2 if ("double" in act or "dbl" in act) else int(args.get("num_clicks", 1))

        # click -> button for mouse_click
        if name in ("mouse_click", "click") and "button" not in args and "click" in args:
            args["button"] = args.get("click")

        allowed = allow.get(name)
        if allowed is None:
            tmp = dict(args)
            tmp.pop("action", None)
            tmp.pop("coordinate", None)
            return tmp

        for k in allowed:
            if k in args and args[k] is not None:
                res[k] = args[k]

        # Normalize unit for scrolling
        if name in ("mouse_scroll", "scroll"):
            unit = str(res.get("unit", "px")).lower()
            res["unit"] = "px" if unit in ("px", "pixel", "pixels") else "step"

        return res

    def _ensure_ctx_memory(self, ctx: CtxItem) -> Dict[str, Dict[str, str]]:
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        if "anthropic_computer" not in ctx.extra or not isinstance(ctx.extra["anthropic_computer"], dict):
            ctx.extra["anthropic_computer"] = {
                "buffers": {},
                "index_to_id": {},
                "active_ids": [],
            }
        else:
            mem = ctx.extra["anthropic_computer"]
            if "buffers" not in mem:
                mem["buffers"] = {}
            if "index_to_id" not in mem:
                mem["index_to_id"] = {}
            if "active_ids" not in mem or not isinstance(mem["active_ids"], list):
                mem["active_ids"] = []
        return ctx.extra["anthropic_computer"]

    @staticmethod
    def _safe_json_loads(s: str) -> Optional[Any]:
        if not isinstance(s, str):
            return None
        s = s.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            try:
                fixed = s
                if fixed.count("{") > fixed.count("}"):
                    fixed += "}" * (fixed.count("{") - fixed.count("}"))
                if fixed.count("[") > fixed.count("]"):
                    fixed += "]" * (fixed.count("[") - fixed.count("]"))
                return json.loads(fixed)
            except Exception:
                return None

    @staticmethod
    def _gen_id(prefix: str = "ac") -> str:
        return f"{prefix}-{int(time.time() * 1000)}"

    @staticmethod
    def _prune_none(d: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove keys with None values to avoid passing None to Worker.
        """
        try:
            return {k: v for k, v in d.items() if v is not None}
        except Exception:
            return d