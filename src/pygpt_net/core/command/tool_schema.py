#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Any, Dict, List, Literal

from llama_index.core.bridge.pydantic import ConfigDict, Field, create_model
from llama_index.core.tools import ToolMetadata


def _field_type(prop: dict):
    value_type = str((prop or {}).get("type") or "string")
    enum = (prop or {}).get("enum")
    if isinstance(enum, list) and enum:
        try:
            return Literal.__getitem__(tuple(enum))
        except Exception:
            pass
    if value_type == "integer":
        return int
    if value_type == "number":
        return float
    if value_type == "boolean":
        return bool
    if value_type == "array":
        return List[_field_type((prop or {}).get("items") or {})]
    if value_type == "object":
        # Google GenAI FunctionDeclaration rejects JSON Schema's
        # additionalProperties field. Pydantic emits it for Dict[str, Any],
        # so keep opaque object parameters as Any here. The original explicit
        # PyGPT JSON schema is still preserved by get_parameters_dict() for
        # providers that consume it directly.
        return Any
    return str


def build_fn_schema(name: str, schema: dict):
    """Build a Pydantic function schema from PyGPT's JSON tool schema.

    LlamaIndex providers normally use ``ToolMetadata.get_parameters_dict()``,
    while GoogleGenAI 0.14.23 converts ``metadata.fn_schema`` directly. Keeping
    both representations synchronized prevents provider-specific argument loss.
    """
    schema = schema or {"type": "object", "properties": {}}
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    fields = {}
    for key, prop in properties.items():
        prop = prop if isinstance(prop, dict) else {}
        annotation = _field_type(prop)
        default = ... if key in required else prop.get("default", None)
        fields[str(key)] = (
            annotation,
            Field(default=default, description=str(prop.get("description") or "")),
        )
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in str(name or "Tool"))
    return create_model(
        f"PyGPTTool_{safe_name}",
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )


class JsonSchemaToolMetadata(ToolMetadata):
    """ToolMetadata backed by the same explicit JSON schema for all providers."""

    def __init__(self, name: str, description: str, schema: dict):
        self.schema = schema or {"type": "object", "properties": {}}
        super().__init__(
            name=name,
            description=description,
            fn_schema=build_fn_schema(name, self.schema),
        )

    def get_parameters_dict(self) -> Dict[str, Any]:
        return {
            k: v for k, v in self.schema.items()
            if k in ("type", "properties", "required", "definitions", "$defs")
        }
