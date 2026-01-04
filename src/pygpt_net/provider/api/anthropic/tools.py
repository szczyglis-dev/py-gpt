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
from typing import List, Any, Dict, Optional

from pygpt_net.item.model import ModelItem


class Tools:
    def __init__(self, window=None):
        """
        Tools mapper for Anthropic Messages API.

        :param window: Window instance
        """
        self.window = window

    def _sanitize_schema(self, schema: Any) -> Any:
        """
        Sanitize JSON Schema dict for Anthropic input_schema.

        - Remove unsupported or risky keywords.
        - Normalize 'type'.
        - Ensure properties/items recursively valid.

        :param schema: JSON Schema (dict or list)
        :return: Sanitized JSON Schema (dict)
        """
        # 1) entry point: if list, take the first element
        if isinstance(schema, list):
            # If it's a list of schemas/types, take the first one (after filtering out empty ones)
            return self._sanitize_schema(schema[0]) if schema else {}

        if not isinstance(schema, dict):
            return schema

        # 2) remove unsupported keys
        banned = {
            "unevaluatedProperties",
            "$defs", "$ref", "$schema", "$id",
            "examples", "readOnly", "writeOnly", "nullable",
            "dependentSchemas", "dependentRequired",
            "oneOf", "anyOf", "allOf", "patternProperties", "dependencies",
            "additional_properties",  # underscore
            "additionalProperties",  # camelCase
        }
        for k in list(schema.keys()):
            if k in banned:
                schema.pop(k, None)

        # 3) normalize 'type'
        t = schema.get("type")

        # a) list of types -> take the first non-null
        if isinstance(t, list):
            t_no_null = [x for x in t if isinstance(x, str) and x.lower() != "null"]
            schema["type"] = t_no_null[0] if t_no_null else "object"
            t = schema["type"]

        # b) if 'type' is not a string (e.g., dict), try to infer or remove it
        if not isinstance(t, str):
            if "properties" in schema:
                schema["type"] = "object"
            elif "items" in schema:
                schema["type"] = "array"
            elif "enum" in schema and isinstance(schema["enum"], list) and all(
                    isinstance(x, str) for x in schema["enum"]):
                schema["type"] = "string"
            else:
                # no reasonable type — leave without 'type' and continue
                schema.pop("type", None)
        else:
            schema["type"] = t.lower()

        # Safe form of type for further comparisons
        t_val = schema.get("type")
        type_l = t_val.lower() if isinstance(t_val, str) else ""

        # 4) enum only for string
        if "enum" in schema and type_l != "string":
            schema.pop("enum", None)

        # 5) Object
        if type_l == "object":
            props = schema.get("properties")
            if not isinstance(props, dict):
                props = {}
            clean_props: Dict[str, Any] = {}
            for pname, pval in props.items():
                clean_props[pname] = self._sanitize_schema(pval)
            schema["properties"] = clean_props

            req = schema.get("required")
            if not (isinstance(req, list) and all(isinstance(x, str) for x in req) and len(req) > 0):
                schema.pop("required", None)

        # 6) Array
        elif type_l == "array":
            items = schema.get("items")
            if isinstance(items, list):
                items = items[0] if items else {"type": "string"}
            if not isinstance(items, dict):
                items = {"type": "string"}
            schema["items"] = self._sanitize_schema(items)

        # 7) Recursion over remaining nestings,
        #    but skip 'properties' and 'items' — we've already sanitized them
        for k, v in list(schema.items()):
            if k in ("properties", "items"):
                continue
            if isinstance(v, dict):
                schema[k] = self._sanitize_schema(v)
            elif isinstance(v, list):
                schema[k] = [self._sanitize_schema(x) for x in v]

        return schema

    def prepare(self, model: ModelItem, functions: list) -> List[dict]:
        """
        Prepare Anthropic tool definitions: [{"name","description","input_schema"}].

        :param model: ModelItem
        :param functions: List of app function dicts
        :return: List of tool dicts for Anthropic
        """
        if not functions or not isinstance(functions, list):
            return []

        tools: List[dict] = []
        for fn in functions:
            name = str(fn.get("name") or "").strip()
            if not name:
                continue
            desc = fn.get("desc") or ""

            params: Optional[dict] = {}
            if fn.get("params"):
                try:
                    params = json.loads(fn["params"])
                except Exception:
                    params = {}
                params = self._sanitize_schema(params or {})
                if not params.get("type"):
                    params["type"] = "object"

            # pass through tool as client tool
            tool_def = {
                "name": name,
                "description": desc,
                "input_schema": params or {"type": "object"},
            }

            # optional: allow defer_loading for tool search when configured per-tool (kept compatible)
            if isinstance(fn, dict) and fn.get("defer_loading") is True:
                tool_def["defer_loading"] = True

            tools.append(tool_def)

        return tools

    def merge_tools_dedup(self, primary: List[dict], secondary: List[dict]) -> List[dict]:
        """
        Remove duplicate tools, preserving order:

        - First from primary list
        - Then from secondary list if not already present

        Dedup rules:
          * Tools with a 'name' are deduped by name.
          * MCP toolsets (type == 'mcp_toolset') are deduped by (type, mcp_server_name).
          * Tools without a 'name' use (type) as a fallback key.

        :param primary: Primary list of tool dicts
        :param secondary: Secondary list of tool dicts
        :return: Merged list of tool dicts without duplicates
        """
        def key_for(t: dict) -> str:
            name = t.get("name")
            if name:
                return f"name::{name}"
            ttype = t.get("type")
            if ttype == "mcp_toolset":
                return f"mcp::{t.get('mcp_server_name', '')}"
            return f"type::{ttype}"

        result: List[dict] = []
        seen = set()

        for t in primary or []:
            k = key_for(t)
            if k not in seen:
                seen.add(k)
                result.append(t)

        for t in secondary or []:
            k = key_for(t)
            if k in seen:
                continue
            seen.add(k)
            result.append(t)

        return result

    def get_all_tools(self, model: ModelItem, functions: list) -> List[dict]:
        """
        Get combined list of all tools (app functions + remote tools) for Anthropic.

        :param model: ModelItem
        :param functions: List of app function dicts
        :return: Combined list of tool dicts
        """
        base_tools = self.prepare(model, functions)
        remote_tools = self.window.core.api.anthropic.remote_tools.build_remote_tools(model)
        return self.merge_tools_dedup(base_tools, remote_tools)