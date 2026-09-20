from types import SimpleNamespace

from pygpt_net.core.realtime.shared.tools import (
    build_function_responses_payload,
    build_tool_outputs_payload,
    prepare_tools_for_response,
    prepare_tools_for_session,
    sanitize_function_tools,
    sanitize_remote_tools,
    tools_signature,
)


CALLS = [
    {"id": "item-1", "call_id": "call-1", "function": {"name": "alpha"}},
    {"id": "item-2", "call_id": "call-2", "function": {"name": "beta"}},
    {"id": "item-3", "call_id": "call-3", "function": {"name": "alpha"}},
]


def test_sanitize_function_tools_flattens_legacy_and_defaults_schema():
    tools = [
        {"type": "function", "function": {"name": "a", "description": "A", "parameters": {"type": "object"}, "strict": True}},
        {"name": "b", "description": "B", "parameters": None},
        {"type": "mcp", "name": "skip"},
        {"type": "function", "description": "missing-name"},
        "bad",
    ]
    out = sanitize_function_tools(tools)
    assert [x["name"] for x in out] == ["a", "b"]
    assert out[0]["strict"] is True
    assert out[1]["parameters"] == {"type": "object", "properties": {}}
    assert sanitize_function_tools(None) == []


def test_sanitize_remote_tools_allows_function_and_mcp_only():
    out = sanitize_remote_tools([
        {"type": "mcp", "server": "x"},
        {"type": "function", "name": "x"},
        {"type": "computer", "name": "skip"},
        {"name": "skip"},
    ])
    assert [x["type"] for x in out] == ["mcp", "function"]


def test_tools_signature_is_order_insensitive_for_tool_list_and_dict_keys():
    a = [{"name": "b", "parameters": {"z": 1, "a": [2, 1]}}, {"name": "a"}]
    b = [{"name": "a"}, {"parameters": {"a": [2, 1], "z": 1}, "name": "b"}]
    assert tools_signature(a) == tools_signature(b)


def test_prepare_tools_for_session_and_response():
    opts = SimpleNamespace(
        tools=[{"name": "fn", "parameters": {"type": "object"}}],
        remote_tools=[{"type": "mcp", "server": "srv"}],
        tool_choice="required",
    )
    session = prepare_tools_for_session(opts)
    assert session[0]["type"] == "mcp" and session[1]["name"] == "fn"
    response, choice = prepare_tools_for_response(opts)
    assert response[0]["name"] == "fn" and choice == "required"


def test_build_tool_outputs_matches_call_id_name_and_serializes_objects():
    results = [
        {"call_id": "call-2", "response": {"ok": True}},
        {"name": "alpha", "result": [1, 2]},
    ]
    out = build_tool_outputs_payload(results, CALLS)
    assert out == [
        {"call_id": "call-2", "previous_item_id": "item-2", "output": '{"ok": true}'},
        {"call_id": "call-1", "previous_item_id": "item-1", "output": "[1, 2]"},
    ]


def test_build_tool_outputs_accepts_wrapped_and_mapping_shapes():
    wrapped = {"tool_outputs": [{"id": "item-1", "content": "done"}]}
    assert build_tool_outputs_payload(wrapped, CALLS) == [
        {"call_id": "call-1", "previous_item_id": "item-1", "output": "done"}
    ]
    mapped = build_tool_outputs_payload({"beta": 7}, CALLS)
    assert mapped == [{"call_id": "call-2", "previous_item_id": "item-2", "output": "7"}]
    scalar = build_tool_outputs_payload(None, CALLS)
    assert scalar == [{"call_id": "call-1", "previous_item_id": "item-1", "output": ""}]
    assert build_tool_outputs_payload("x", []) == []


def test_build_function_responses_supports_wrapped_list_and_mapping_shapes():
    wrapped = {"function_responses": [{"id": "custom", "name": "x", "response": {"ok": True}}]}
    assert build_function_responses_payload(wrapped, CALLS) == [
        {"id": "custom", "name": "x", "response": {"ok": True}}
    ]

    out = build_function_responses_payload([
        {"name": "alpha", "result": "A"},
        {"id": "item-2", "name": "beta", "output": {"b": 2}},
        "fallback",
    ], CALLS)
    assert out[0] == {"id": "item-1", "name": "alpha", "response": {"result": "A"}}
    assert out[1] == {"id": "item-2", "name": "beta", "response": {"b": 2}}
    assert out[2]["response"] == {"result": "fallback"}

    mapped = build_function_responses_payload({"alpha": 1, "beta": {"ok": True}}, CALLS)
    assert mapped[0]["name"] == "alpha" and mapped[0]["response"] == {"result": "1"}
    assert mapped[1]["name"] == "beta" and mapped[1]["response"] == {"ok": True}
