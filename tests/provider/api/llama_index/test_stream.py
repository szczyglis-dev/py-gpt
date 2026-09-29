#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace

from pygpt_net.provider.api.llama_index.stream import (
    extract_tool_calls_from_message,
    message_has_tool_calls,
    process_llama_chat,
)


def test_extract_tool_calls_from_chat_completions_message():
    message = SimpleNamespace(
        blocks=[],
        additional_kwargs={
            "tool_calls": [{
                "id": "call_1",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path":"a.txt"}',
                },
            }]
        },
    )

    calls = extract_tool_calls_from_message(message)

    assert calls == [{
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "read_file",
            "arguments": '{"path":"a.txt"}',
        },
    }]
    assert message_has_tool_calls(message) is True


def test_extract_tool_calls_from_responses_api_tool_call_block():
    message = SimpleNamespace(
        blocks=[SimpleNamespace(
            tool_call_id="call_2",
            tool_name="read_file",
            tool_kwargs={"path": "b.txt"},
        )],
        additional_kwargs={},
    )

    calls = extract_tool_calls_from_message(message)

    assert calls == [{
        "id": "call_2",
        "type": "function",
        "function": {
            "name": "read_file",
            "arguments": {"path": "b.txt"},
        },
    }]
    assert message_has_tool_calls(message) is True


def test_process_llama_chat_keeps_latest_cumulative_tool_call_snapshot():
    state = SimpleNamespace(tool_calls=[])
    first = SimpleNamespace(
        delta="",
        message=SimpleNamespace(
            blocks=[],
            additional_kwargs={
                "tool_calls": [{
                    "id": "call_1",
                    "function": {"name": "a", "arguments": "{}"},
                }]
            },
        ),
    )
    second = SimpleNamespace(
        delta="done",
        message=SimpleNamespace(
            blocks=[],
            additional_kwargs={
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "a", "arguments": "{}"},
                    },
                    {
                        "id": "call_2",
                        "function": {"name": "b", "arguments": "{}"},
                    },
                ]
            },
        ),
    )

    assert process_llama_chat(state, first) == ""
    assert [call["id"] for call in state.tool_calls] == ["call_1"]

    assert process_llama_chat(state, second) == "done"
    assert [call["id"] for call in state.tool_calls] == ["call_1", "call_2"]
