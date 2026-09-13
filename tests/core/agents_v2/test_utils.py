#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from types import SimpleNamespace

import pygpt_net.core.agents_v2.utils as utils_module
from pygpt_net.core.agents_v2.utils import (
    effective_iteration_limit,
    json_safe_tool_result,
    json_safe_tool_value,
    legacy_worker_context_record,
    result_text,
    short_status_text,
    supports_function_calling,
    tool_event_value,
    tool_result_value,
    translated_status,
)


def test_effective_iteration_limit_maps_zero_to_unlimited_and_preserves_positive_values():
    assert effective_iteration_limit(0) == sys.maxsize
    assert effective_iteration_limit(1) == 1
    assert effective_iteration_limit(48) == 48


def test_tool_event_value_supports_dicts_objects_and_first_non_empty_key():
    assert tool_event_value({"name": "", "tool_name": "search"}, "name", "tool_name") == "search"
    event = SimpleNamespace(name=None, tool="read_file")
    assert tool_event_value(event, "name", "tool") == "read_file"
    assert tool_event_value({}, "missing") is None


def test_json_safe_tool_value_and_result_keep_argument_and_response_contracts_distinct():
    assert json_safe_tool_value(None) == {}
    assert json_safe_tool_result(None) == ""
    assert json_safe_tool_value('{"q": 1}') == {"q": 1}
    assert json_safe_tool_result('[1, 2]') == [1, 2]
    assert json_safe_tool_value("plain") == "plain"
    assert json_safe_tool_result("plain") == "plain"
    assert json_safe_tool_value({"x": complex(1, 2)}) == {"x": "(1+2j)"}


def test_tool_result_value_unwraps_content_and_preserves_valid_empty_output():
    assert tool_result_value({"tool_output": {"content": "done"}}) == "done"
    assert tool_result_value(SimpleNamespace(output=SimpleNamespace(content="ok"))) == "ok"
    assert tool_result_value({"result": ""}) == ""
    assert tool_result_value({}) == ""


def test_status_and_result_helpers_handle_provider_metadata_and_bad_translation_placeholders(monkeypatch):
    assert supports_function_calling(SimpleNamespace(metadata=SimpleNamespace(is_function_calling_model=True))) is True
    assert supports_function_calling(SimpleNamespace()) is False
    assert short_status_text("  many   spaces here  ") == "many spaces here"
    assert short_status_text("abcdefghij", limit=7) == "abcd..."

    monkeypatch.setattr(utils_module, "trans", lambda key: "Tool: {tool}")
    assert translated_status("status.tool", tool="search") == "Tool: search"
    assert translated_status("status.tool") == "Tool: {tool}"

    assert result_text("  answer  ") == "answer"
    assert result_text(SimpleNamespace(response=SimpleNamespace(content=" response "))) == "response"
    assert result_text(SimpleNamespace(content=" content ")) == "content"
    assert result_text(None) == ""


def test_legacy_worker_context_record_normalizes_old_field_names_and_timestamp():
    assert legacy_worker_context_record("invalid") is None
    assert legacy_worker_context_record({
        "worker_id": 7,
        "worker_name": "Researcher",
        "task": "Find data",
        "output_text": "Done",
        "output_created_at": "123",
    }) == {
        "id": "7",
        "name": "Researcher",
        "input": "Find data",
        "output": "Done",
        "created_at": 123,
    }
    assert legacy_worker_context_record({"created_at": "bad"})["created_at"] == 0
