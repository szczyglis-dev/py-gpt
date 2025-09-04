#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 01:00:00                  #
# ================================================== #

import json
from typing import List, Any, Optional


class Tools:
    def __init__(self, window=None):
        """
        Tools mapper for xAI Chat Completions-compatible schema.

        Input: app 'functions' list with keys: name, desc, params (JSON Schema string).
        Output: list of dicts with keys: name, description, parameters.

        :param window: Window instance
        """
        self.window = window

    def _sanitize_schema(self, schema: Any) -> Any:
        """
        Sanitize JSON Schema for tool parameters:
        - Remove unsupported or risky keywords.
        - Normalize 'type'.
        - Ensure properties/items recursively valid.

        :param schema: JSON Schema (dict or list)
        :return: Sanitized JSON Schema (dict)
        """
        if isinstance(schema, list):
            return self._sanitize_schema(schema[0]) if schema else {}

        if not isinstance(schema, dict):
            return schema

        banned = {
            "$defs", "$ref", "$schema", "$id",
            "oneOf", "anyOf", "allOf",
            "patternProperties", "dependentSchemas", "dependentRequired",
            "unevaluatedProperties", "nullable", "readOnly", "writeOnly",
            "examples", "additional_properties", "additionalProperties",
        }
        for k in list(schema.keys()):
            if k in banned:
                schema.pop(k, None)

        t = schema.get("type")
        if isinstance(t, list):
            t_no_null = [x for x in t if x != "null"]
            schema["type"] = t_no_null[0] if t_no_null else "object"

        # Recurse
        if (schema.get("type") or "").lower() == "object":
            props = schema.get("properties")
            if not isinstance(props, dict):
                props = {}
            clean = {}
            for k, v in props.items():
                clean[k] = self._sanitize_schema(v)
            schema["properties"] = clean
            req = schema.get("required")
            if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
                schema.pop("required", None)
            elif len(req) == 0:
                schema.pop("required", None)

        if (schema.get("type") or "").lower() == "array":
            items = schema.get("items")
            if isinstance(items, list) and items:
                items = items[0]
            if not isinstance(items, dict):
                items = {"type": "string"}
            schema["items"] = self._sanitize_schema(items)

        return schema

    def prepare(self, functions: list) -> List[dict]:
        """
        Prepare xAI tools list (OpenAI-compatible schema) from app functions list.

        Returns [] if no functions provided.

        :param functions: List of functions with keys: name (str), desc (str), params (JSON Schema str)
        :return: List of tools with keys: name (str), description (str), parameters (dict)
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
            else:
                params = {"type": "object"}

            tools.append({
                "name": name,
                "description": desc,
                "parameters": params,
            })
        return tools