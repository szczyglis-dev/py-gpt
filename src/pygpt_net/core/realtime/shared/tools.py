#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import json
from typing import Any, Optional, List, Dict

def sanitize_function_tools(tools) -> list:
    """
    OpenAI: Normalize function tools into a flat dict shape:
      {"type":"function","name","description","parameters", ...}
    Accepts legacy {"type":"function","function":{...}} and flattens it.
    """
    out = []
    if not tools:
        return out
    for t in tools:
        if not isinstance(t, dict):
            continue
        tt = dict(t)
        ttype = (tt.get("type") or "function").lower()
        if ttype != "function":
            continue
        if isinstance(tt.get("function"), dict):
            fn = tt["function"]
            nt = {"type": "function"}
            for k in ("name", "description", "parameters", "strict", "strict_schema"):
                if k in fn and fn[k] is not None:
                    nt[k] = fn[k]
            if "description" not in nt and tt.get("description"):
                nt["description"] = tt["description"]
        else:
            nt = {
                "type": "function",
                "name": tt.get("name"),
                "description": tt.get("description"),
                "parameters": tt.get("parameters"),
            }
            for k in ("strict", "strict_schema"):
                if k in tt:
                    nt[k] = tt[k]
        if not nt.get("name"):
            continue
        if not isinstance(nt.get("parameters"), dict):
            nt["parameters"] = {"type": "object", "properties": {}}
        out.append(nt)
    return out

def sanitize_remote_tools(remote_tools) -> list:
    """OpenAI: Pass-through for non-function tools (ensure lowercased 'type')."""
    allowed = {"function", "mcp"}  # Realtime accepts only these
    out = []
    if not remote_tools:
        return out
    for t in remote_tools:
        if not isinstance(t, dict):
            continue
        tt = dict(t)
        ttype = tt.get("type")
        if not ttype:
            continue
        if allowed is not None and ttype not in allowed:
            continue
        tt["type"] = str(ttype).lower()
        out.append(tt)
    return out

def tools_signature(tools_list: list) -> str:
    """Order-insensitive stable signature for tools list."""
    def canon(obj):
        if isinstance(obj, dict):
            return {k: canon(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [canon(x) for x in obj]
        return obj
    try:
        canon_items = [json.dumps(canon(t), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                       for t in (tools_list or [])]
        canon_items.sort()
        return "|".join(canon_items)
    except Exception:
        return str(tools_list)

def prepare_tools_for_session(opts) -> list:
    """Compose session.tools from opts.remote_tools + opts.tools."""
    fn = sanitize_function_tools(getattr(opts, "tools", None))
    rt = sanitize_remote_tools(getattr(opts, "remote_tools", None))
    return (rt or []) + (fn or [])

def prepare_tools_for_response(opts) -> tuple[list, Optional[str]]:
    """Compose per-response function tools and tool_choice."""
    fn = sanitize_function_tools(getattr(opts, "tools", None))
    tool_choice = getattr(opts, "tool_choice", None)
    return fn, tool_choice

def build_tool_outputs_payload(results, last_tool_calls: List[Dict]) -> List[Dict]:
    """
    Normalize 'results' into:
      [{"call_id": str, "previous_item_id": str|None, "output": str}]
    Matching priority: call_id -> item.id -> function name -> first unused.
    """
    calls = list(last_tool_calls or [])
    by_id = {c.get("id") or "": c for c in calls if c.get("id")}
    by_call = {c.get("call_id") or "": c for c in calls if c.get("call_id")}
    by_name: dict[str, list] = {}
    for c in calls:
        nm = ((c.get("function") or {}).get("name") or "").strip()
        if nm:
            by_name.setdefault(nm, []).append(c)

    used: set[str] = set()
    def to_str(val) -> str:
        if val is None:
            return ""
        if isinstance(val, (dict, list)):
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return str(val)
        return str(val)

    def pick_name(name: str):
        arr = by_name.get(name) or []
        for cand in arr:
            cid = cand.get("call_id") or ""
            if cid and cid not in used:
                used.add(cid)
                return cand
        return None

    def pick_first():
        for cand in calls:
            cid = cand.get("call_id") or ""
            if cid and cid not in used:
                used.add(cid)
                return cand
        return None

    out: list[dict] = []

    if isinstance(results, dict) and ("function_responses" in results or "tool_outputs" in results):
        items = results.get("function_responses") or results.get("tool_outputs") or []
        for it in items:
            if not isinstance(it, dict):
                c = pick_first()
                if c:
                    out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(it)})
                continue
            cid = it.get("call_id") or it.get("id") or it.get("tool_call_id") or ""
            nm = it.get("name") or ""
            resp = it.get("response")
            if resp is None:
                resp = it.get("result") or it.get("output") or it.get("content")
            c = by_call.get(cid) or by_id.get(cid) or (pick_name(nm) if nm else pick_first())
            if c:
                out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(resp)})
        return out

    if isinstance(results, list):
        for it in results:
            if not isinstance(it, dict):
                c = pick_first()
                if c:
                    out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(it)})
                continue
            cid = it.get("call_id") or it.get("id") or it.get("tool_call_id") or ""
            nm = it.get("name") or ""
            resp = it.get("response")
            if resp is None:
                resp = it.get("result") or it.get("output") or it.get("content")
            c = by_call.get(cid) or by_id.get(cid) or (pick_name(nm) if nm else pick_first())
            if c:
                out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(resp)})
        return out

    if isinstance(results, dict):
        for k, v in results.items():
            if not isinstance(k, str):
                continue
            c = by_call.get(k) or by_id.get(k) or pick_name(k)
            if c:
                out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(v)})
        return out

    c = pick_first()
    if c:
        out.append({"call_id": c.get("call_id"), "previous_item_id": c.get("id"), "output": to_str(results)})
    return out

def build_function_responses_payload(results, last_tool_calls: List[Dict]) -> List[Dict]:
    """
    Produce neutral list of dicts for Google:
      [{"id": "...", "name": "...", "response": {...}}]
    Provider converts to gtypes.FunctionResponse downstream.
    """
    calls = list(last_tool_calls or [])
    by_id = {c.get("id") or "": c for c in calls if c.get("id")}
    by_name: dict[str, list] = {}
    for c in calls:
        nm = (c.get("function") or {}).get("name") or ""
        if nm:
            by_name.setdefault(nm, []).append(c)

    used_ids: set[str] = set()

    def pick_id_for_name(name: str) -> str:
        arr = by_name.get(name) or []
        for cand in arr:
            cid = cand.get("id") or ""
            if cid and cid not in used_ids:
                used_ids.add(cid)
                return cid
        return ""

    def to_resp_dict(val):
        if isinstance(val, dict):
            return val
        return {"result": str(val)}

    out: list = []

    if isinstance(results, dict) and "function_responses" in results:
        items = results.get("function_responses") or []
        for it in items:
            fid = it.get("id") or ""
            nm = it.get("name") or ""
            resp = it.get("response")
            if resp is None:
                resp = it.get("result") or it.get("output") or it.get("content") or {}
            out.append({"id": fid, "name": nm, "response": to_resp_dict(resp)})
        return out

    if isinstance(results, list):
        for it in results:
            if not isinstance(it, dict):
                if calls:
                    ref = calls[0]
                    cid = ref.get("id") or ""
                    nm = (ref.get("function") or {}).get("name") or ""
                    used_ids.add(cid)
                    out.append({"id": cid, "name": nm, "response": to_resp_dict(it)})
                continue
            fid = it.get("id") or it.get("call_id") or it.get("tool_call_id") or ""
            nm = it.get("name") or ""
            resp = it.get("response")
            if resp is None:
                resp = it.get("result") or it.get("output") or it.get("content") or {}
            if not fid and nm:
                fid = pick_id_for_name(nm)
            if fid:
                used_ids.add(fid)
            out.append({"id": fid, "name": nm, "response": to_resp_dict(resp)})
        return out

    if isinstance(results, dict):
        for k, v in results.items():
            if not isinstance(k, str):
                continue
            if k in by_id:
                nm = (by_id[k].get("function") or {}).get("name") or ""
                used_ids.add(k)
                out.append({"id": k, "name": nm, "response": to_resp_dict(v)})
            else:
                nm = k
                fid = pick_id_for_name(nm)
                out.append({"id": fid, "name": nm, "response": to_resp_dict(v)})
        return out

    return out