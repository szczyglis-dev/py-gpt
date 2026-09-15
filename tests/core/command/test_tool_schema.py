#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, get_args, get_origin, Literal

import pytest

from pygpt_net.core.command.tool_schema import (
    JsonSchemaToolMetadata,
    _field_type,
    build_fn_schema,
)


def test_field_type_maps_json_schema_primitives_arrays_objects_and_default_string():
    assert _field_type({"type": "integer"}) is int
    assert _field_type({"type": "number"}) is float
    assert _field_type({"type": "boolean"}) is bool
    assert _field_type({"type": "object"}) is Any
    assert _field_type({"type": "unknown"}) is str
    assert _field_type({}) is str

    array_type = _field_type({"type": "array", "items": {"type": "integer"}})
    assert get_origin(array_type) is list
    assert get_args(array_type) == (int,)


def test_field_type_builds_literal_for_nonempty_enum():
    field_type = _field_type({"type": "string", "enum": ["a", "b"]})

    assert get_origin(field_type) is Literal
    assert get_args(field_type) == ("a", "b")


def test_build_fn_schema_preserves_required_optional_defaults_and_descriptions():
    model = build_fn_schema("copy-file!", {
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Source path"},
            "overwrite": {"type": "boolean", "default": False, "description": "Overwrite"},
        },
        "required": ["source"],
    })

    with pytest.raises(Exception):
        model()

    value = model(source="a", overwrite=True, ignored="drop")
    assert value.source == "a"
    assert value.overwrite is True
    assert not hasattr(value, "ignored")
    schema = model.model_json_schema()
    assert schema["properties"]["source"]["description"] == "Source path"
    assert schema["properties"]["overwrite"]["default"] is False


def test_build_fn_schema_opaque_object_does_not_emit_additional_properties_for_dict_type():
    model = build_fn_schema("object", {
        "type": "object",
        "properties": {
            "payload": {"type": "object"},
        },
    })

    payload_schema = model.model_json_schema()["properties"]["payload"]

    assert "additionalProperties" not in payload_schema


def test_build_fn_schema_accepts_empty_schema():
    model = build_fn_schema("empty", None)

    value = model(extra="ignored")
    assert value.model_dump() == {}


def test_json_schema_tool_metadata_exposes_same_explicit_schema_for_provider_adapters():
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "$defs": {"X": {"type": "string"}},
        "title": "must not leak",
    }

    metadata = JsonSchemaToolMetadata("read_file", "Read a file", schema)

    assert metadata.name == "read_file"
    assert metadata.description == "Read a file"
    assert metadata.get_parameters_dict() == {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "$defs": {"X": {"type": "string"}},
    }
    assert metadata.fn_schema(path="x").path == "x"
