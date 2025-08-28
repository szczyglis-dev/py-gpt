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
        Sanitize JSON Schema dict by removing unsupported keywords and normalizing types.

        1. Remove unsupported keywords like additionalProperties, patternProperties,
           dependencies, oneOf, anyOf, allOf, $ref, $defs, examples, readOnly, writeOnly.
        2. Normalize 'type' to a single value (e.g., if it's a list, take the first non-null type).
        3. Ensure 'enum' is only present for string types.
        4. Recursively sanitize nested schemas in 'properties' and 'items'.
        5. Handle arrays by ensuring 'items' is a single schema.
        6. Handle objects by ensuring 'properties' is a dict and 'required' is a list of strings.

        :param schema: Any JSON Schema as dict or list
        :return: Sanitized schema dict
        """
        if isinstance(schema, list):
            return self._sanitize_schema(schema[0]) if schema else {}

        if not isinstance(schema, dict):
            return schema

        banned = {
            "additionalProperties",
            "additional_properties",
            "unevaluatedProperties",
            "patternProperties",
            "dependencies",
            "dependentSchemas",
            "dependentRequired",
            "oneOf",
            "anyOf",
            "allOf",
            "$defs",
            "$ref",
            "$schema",
            "$id",
            "examples",
            "readOnly",
            "writeOnly",
            "nullable",
        }
        for k in list(schema.keys()):
            if k in banned:
                schema.pop(k, None)

        # Union -> first non-null type
        t = schema.get("type")
        if isinstance(t, list):
            t_no_null = [x for x in t if x != "null"]
            schema["type"] = t_no_null[0] if t_no_null else "string"

        # enum only for string
        if "enum" in schema and schema.get("type") not in ("string", "STRING"):
            schema.pop("enum", None)

        # object
        if (schema.get("type") or "").lower() == "object":
            props = schema.get("properties")
            if not isinstance(props, dict):
                props = {}
            clean_props: Dict[str, Any] = {}
            for pname, pval in props.items():
                clean_props[pname] = self._sanitize_schema(pval)
            schema["properties"] = clean_props

            req = schema.get("required")
            if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
                schema.pop("required", None)
            elif len(req) == 0:
                schema.pop("required", None)

        # array
        if (schema.get("type") or "").lower() == "array":
            items = schema.get("items")
            if isinstance(items, list) and items:
                items = items[0]
            if not isinstance(items, dict):
                items = {"type": "string"}
            schema["items"] = self._sanitize_schema(items)

        # recursive sanitize
        for k, v in list(schema.items()):
            if isinstance(v, dict):
                schema[k] = self._sanitize_schema(v)
            elif isinstance(v, list):
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