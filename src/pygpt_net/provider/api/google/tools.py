#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

import json
from typing import List, Any, Dict, Optional

from google.genai import types as gtypes
from pygpt_net.item.model import ModelItem


class Tools:
    def __init__(self, window=None):
        """
        Tools mapper for Google GenAI

        :param window: Window instance
        """
        self.window = window

    # -------- SANITIZER --------
    def _sanitize_schema(self, schema: Any) -> Any:
        """
        Sanitize a JSON Schema dict for Google GenAI (function parameters).

        Key points:
        - Remove unsupported JSON Schema keywords (additionalProperties, oneOf, $ref, ...).
        - Normalize "type" so that it's either a single lowercase string or absent.
          Handle lists (unions), non-string types (e.g., dict), and infer a type when possible.
        - Keep "enum" only when type is string.
        - For objects, sanitize only "properties" (each property's schema) and validate "required".
        - For arrays, sanitize "items" into a single schema (object, not list).
        - Do not recurse into "properties" itself as a map, nor into "required"/"enum" as they are scalars/lists.
        """
        # 1) Fast exits
        if isinstance(schema, list):
            # Only descend into lists of dicts (complex schemas). For scalar lists (required/enum), return as is.
            if schema and all(isinstance(x, dict) for x in schema):
                return [self._sanitize_schema(x) for x in schema]
            return schema

        if not isinstance(schema, dict):
            return schema

        # 2) Remove unsupported/problematic keywords for Google function parameters
        banned = {
            "additionalProperties", "additional_properties",
            "unevaluatedProperties", "patternProperties",
            "dependencies", "dependentSchemas", "dependentRequired",
            "oneOf", "anyOf", "allOf",
            "$defs", "$ref", "$schema", "$id",
            "examples", "readOnly", "writeOnly", "nullable",
        }
        for k in list(schema.keys()):
            if k in banned:
                schema.pop(k, None)

        # 3) Normalize "type" safely
        t = schema.get("type")

        # a) If it's a list (union), pick the first non-null string, otherwise default to "object"
        if isinstance(t, list):
            t_no_null = [x for x in t if isinstance(x, str) and x.lower() != "null"]
            schema["type"] = t_no_null[0] if t_no_null else "object"
            t = schema["type"]

        # b) If "type" is not a string (could be dict or missing), try to infer; otherwise drop it
        if not isinstance(t, str):
            if isinstance(schema.get("properties"), dict):
                schema["type"] = "object"
            elif "items" in schema:
                schema["type"] = "array"
            elif isinstance(schema.get("enum"), list) and all(isinstance(x, str) for x in schema["enum"]):
                schema["type"] = "string"
            else:
                schema.pop("type", None)
        else:
            schema["type"] = t.lower()

        type_l = schema["type"].lower() if isinstance(schema.get("type"), str) else ""

        # 4) Keep enum only for string-typed schemas
        if "enum" in schema and type_l != "string":
            schema.pop("enum", None)

        # 5) Objects: sanitize properties and required
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

        # 6) Arrays: ensure "items" is a single dict schema
        elif type_l == "array":
            items = schema.get("items")
            if isinstance(items, list):
                items = items[0] if items else {"type": "string"}
            if not isinstance(items, dict):
                items = {"type": "string"}
            schema["items"] = self._sanitize_schema(items)

        # 7) Recurse into the remaining nested dict/list values,
        #    but skip "properties", "items", "required", and "enum" (already handled)
        for k, v in list(schema.items()):
            if k in ("properties", "items", "required", "enum"):
                continue
            if isinstance(v, dict):
                schema[k] = self._sanitize_schema(v)
            elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                schema[k] = [self._sanitize_schema(x) for x in v]

        return schema

    # -------- CONVERTER to gtypes.Schema (UPPERCASE) --------
    def _to_gschema(self, schema: Any) -> gtypes.Schema:
        """
        Convert sanitized dict -> google.genai.types.Schema.
        Enforces UPPERCASE type names (OBJECT, ARRAY, STRING, NUMBER, INTEGER, BOOLEAN).

        :param schema: Sanitized JSON Schema as dict
        :return: gtypes.Schema
        """
        TYPE_MAP = {
            "enum": "STRING",
            "ENUM": "STRING",
            "object": "OBJECT",
            "dict": "OBJECT",
            "array": "ARRAY",
            "list": "ARRAY",
            "string": "STRING",
            "number": "NUMBER",
            "float": "NUMBER",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "int": "INTEGER",
            "bool": "BOOLEAN",
            "OBJECT": "OBJECT",
            "DICT": "OBJECT",
            "ARRAY": "ARRAY",
            "LIST": "ARRAY",
            "STRING": "STRING",
            "NUMBER": "NUMBER",
            "FLOAT": "NUMBER",
            "INTEGER": "INTEGER",
            "BOOLEAN": "BOOLEAN",
            "INT": "INTEGER",
            "BOOL": "BOOLEAN",
        }

        if isinstance(schema, gtypes.Schema):
            return schema

        if not isinstance(schema, dict):
            return gtypes.Schema(type="STRING")

        t = TYPE_MAP.get(str(schema.get("type", "OBJECT")).upper(), "OBJECT")
        desc = schema.get("description")
        fmt = schema.get("format")
        enum = schema.get("enum") if isinstance(schema.get("enum"), list) else None
        req = schema.get("required") if isinstance(schema.get("required"), list) else None

        gs = gtypes.Schema(
            type=t,
            description=desc,
            format=fmt,
            enum=enum,
            required=[x for x in (req or []) if isinstance(x, str)] or None,
        )

        props = schema.get("properties")
        if isinstance(props, dict):
            gs.properties = {k: self._to_gschema(v) for k, v in props.items()}

        items = schema.get("items")
        if isinstance(items, dict):
            gs.items = self._to_gschema(items)

        return gs

    def prepare(self, model: ModelItem, functions: list) -> List[gtypes.Tool]:
        """
        Prepare Google Function Declarations (types.Tool) for google-genai.

        :param model: ModelItem
        :param functions: List of function definitions as dicts with 'name', 'desc', 'params' (JSON Schema)
        :return: List of gtypes.Tool
        """
        if not functions or not isinstance(functions, list):
            return []

        fds: List[gtypes.FunctionDeclaration] = []
        for function in functions:
            name = str(function.get("name") or "").strip()
            if not name:
                continue

            desc = function.get("desc") or ""
            params: Optional[dict] = {}
            if function.get("params"):
                try:
                    params = json.loads(function["params"])
                except Exception:
                    params = {}

                params = self._sanitize_schema(params or {})
                if not params.get("type"):
                    params["type"] = "object"

            gschema = self._to_gschema(params or {"type": "object"})

            fd = gtypes.FunctionDeclaration(
                name=name,
                description=desc,
                parameters=gschema,
            )
            fds.append(fd)

        return [gtypes.Tool(function_declarations=fds)] if fds else []