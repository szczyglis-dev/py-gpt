#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 18:05:00                  #
# ================================================== #

import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from pygpt_net.core.idx.response import Response


def test_from_react_does_not_call_set_output_or_modify_ctx():
    sentinel_stream = object()
    sentinel_tool_calls = object()
    ctx = SimpleNamespace(set_output=Mock(), stream=sentinel_stream, tool_calls=sentinel_tool_calls)
    r = Response()
    r.from_react(ctx, model=Mock(), llm=None, response=SimpleNamespace(model=Mock()))
    ctx.set_output.assert_called()
    assert ctx.stream is sentinel_stream
    assert ctx.tool_calls is sentinel_tool_calls


def test_from_index_calls_set_output_with_str_response():
    ctx = SimpleNamespace(set_output=Mock())
    response = SimpleNamespace(response="hello world")
    r = Response()
    r.from_index(ctx, model=Mock(), llm=None, response=response)
    ctx.set_output.assert_called_once_with("hello world", "")


def test_from_index_with_none_response_calls_set_output_with_string_none():
    ctx = SimpleNamespace(set_output=Mock())
    response = SimpleNamespace(response=None)
    r = Response()
    r.from_index(ctx, model=Mock(), llm=None, response=response)
    ctx.set_output.assert_called_once_with("None", "")


def test_from_index_extracts_local_tagged_reasoning_to_extra():
    ctx = SimpleNamespace(set_output=Mock(), extra={})
    response = SimpleNamespace(response="<think>internal reasoning</think>\n\nfinal answer")
    model = SimpleNamespace(
        provider="ollama",
        llama_index={},
        is_ollama=lambda: True,
    )
    r = Response()
    r.from_index(ctx, model=model, llm=None, response=response)

    ctx.set_output.assert_called_once_with("final answer", "")
    assert ctx.extra["reasoning"] == {
        "provider": "ollama",
        "type": "thinking",
        "text": "internal reasoning",
        "raw": True,
        "visible": True,
        "encrypted": False,
    }


def test_from_index_keeps_think_tags_for_non_local_model():
    ctx = SimpleNamespace(set_output=Mock(), extra={})
    response = SimpleNamespace(response="<think>ordinary text</think> final answer")
    model = SimpleNamespace(
        provider="openai",
        llama_index={},
        is_ollama=lambda: False,
    )
    r = Response()
    r.from_index(ctx, model=model, llm=None, response=response)

    ctx.set_output.assert_called_once_with("<think>ordinary text</think> final answer", "")
    assert ctx.extra == {}


def test_from_index_extracts_unclosed_local_think_block():
    ctx = SimpleNamespace(set_output=Mock(), extra={})
    response = SimpleNamespace(response="<think>partial reasoning")
    model = SimpleNamespace(
        provider="local_ai",
        llama_index={},
        is_ollama=lambda: False,
    )
    r = Response()
    r.from_index(ctx, model=model, llm=None, response=response)

    ctx.set_output.assert_called_once_with("", "")
    assert ctx.extra["reasoning"]["text"] == "partial reasoning"
    assert ctx.extra["reasoning"]["type"] == "thinking"


def test_from_llm_sets_output_and_unpacks_tool_calls_when_message_present():
    ctx = SimpleNamespace(set_output=Mock(), tool_calls=None, urls=[])
    response = SimpleNamespace(message=SimpleNamespace(content="content"))
    llm = Mock()
    llm.pop_pygpt_urls.return_value = []
    tool_calls = [{"name": "tool1"}]
    llm.get_tool_calls_from_response.return_value = tool_calls
    unpacked = [{"unpacked": True}]
    command_mock = Mock()
    command_mock.unpack_tool_calls_from_llama.return_value = unpacked
    window = SimpleNamespace(core=SimpleNamespace(command=command_mock))
    r = Response(window=window)
    r.from_llm(ctx, model=Mock(), llm=llm, response=response)
    ctx.set_output.assert_called_once_with("content", "")
    llm.get_tool_calls_from_response.assert_called_once_with(response, error_on_no_tool_call=False)
    command_mock.unpack_tool_calls_from_llama.assert_called_once_with(tool_calls)
    assert ctx.tool_calls == unpacked


def test_from_llm_with_none_content_sets_empty_output_and_unpacks_tool_calls():
    ctx = SimpleNamespace(set_output=Mock(), tool_calls="orig", urls=[])
    response = SimpleNamespace(message=SimpleNamespace(content=None))
    llm = Mock()
    llm.pop_pygpt_urls.return_value = []
    tool_calls = []
    llm.get_tool_calls_from_response.return_value = tool_calls
    unpacked = []
    command_mock = Mock()
    command_mock.unpack_tool_calls_from_llama.return_value = unpacked
    window = SimpleNamespace(core=SimpleNamespace(command=command_mock))
    r = Response(window=window)
    r.from_llm(ctx, model=Mock(), llm=llm, response=response)
    ctx.set_output.assert_called_once_with("", "")
    llm.get_tool_calls_from_response.assert_called_once_with(response, error_on_no_tool_call=False)
    command_mock.unpack_tool_calls_from_llama.assert_called_once_with(tool_calls)
    assert ctx.tool_calls == unpacked


def test_from_index_stream_sets_stream_and_clears_output():
    gen = (i for i in range(3))
    ctx = SimpleNamespace(set_output=Mock(), stream=None)
    response = SimpleNamespace(response_gen=gen)
    r = Response()
    r.from_index_stream(ctx, model=Mock(), llm=None, response=response)
    ctx.set_output.assert_called_once_with("", "")
    assert ctx.stream is not gen
    assert list(ctx.stream) == [0, 1, 2]


def test_from_llm_stream_wraps_stream_and_clears_output():
    ctx = SimpleNamespace(set_output=Mock(), stream=None, urls=[])
    chunk = SimpleNamespace(delta="chunk", message=None)
    response = iter([chunk])
    llm = Mock()
    llm.pop_pygpt_urls.return_value = []
    r = Response()
    r.from_llm_stream(ctx, model=Mock(), llm=llm, response=response)

    ctx.set_output.assert_called_once_with("", "")
    assert ctx.stream is not response
    assert list(ctx.stream) == [chunk]


def test_from_llm_stream_preserves_native_tool_call_message():
    tool_message = SimpleNamespace(
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
    chunk = SimpleNamespace(delta=None, message=tool_message)
    chat = SimpleNamespace(prev_message=None)
    debug = SimpleNamespace(info=Mock(), log=Mock())
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(chat=chat), debug=debug)
    )
    ctx = SimpleNamespace(set_output=Mock(), stream=None, urls=[])
    llm = Mock()
    llm.pop_pygpt_urls.return_value = []

    r = Response(window=window)
    r.from_llm_stream(ctx, model=Mock(), llm=llm, response=iter([chunk]))

    assert list(ctx.stream) == [chunk]
    assert chat.prev_message is tool_message
    debug.info.assert_called_once()
    debug.log.assert_not_called()
