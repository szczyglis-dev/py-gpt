#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
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
    r.from_react(ctx, model=Mock(), response=SimpleNamespace(model=Mock()))
    ctx.set_output.assert_called()
    assert ctx.stream is sentinel_stream
    assert ctx.tool_calls is sentinel_tool_calls


def test_from_index_calls_set_output_with_str_response():
    ctx = SimpleNamespace(set_output=Mock())
    response = SimpleNamespace(response="hello world")
    r = Response()
    r.from_index(ctx, model=Mock(), response=response)
    ctx.set_output.assert_called_once_with("hello world", "")


def test_from_index_with_none_response_calls_set_output_with_string_none():
    ctx = SimpleNamespace(set_output=Mock())
    response = SimpleNamespace(response=None)
    r = Response()
    r.from_index(ctx, model=Mock(), response=response)
    ctx.set_output.assert_called_once_with("None", "")


def test_from_llm_sets_output_and_unpacks_tool_calls_when_message_present():
    ctx = SimpleNamespace(set_output=Mock(), tool_calls=None)
    response = SimpleNamespace(message=SimpleNamespace(content="content"))
    llm = Mock()
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
    ctx = SimpleNamespace(set_output=Mock(), tool_calls="orig")
    response = SimpleNamespace(message=SimpleNamespace(content=None))
    llm = Mock()
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
    r.from_index_stream(ctx, model=Mock(), response=response)
    ctx.set_output.assert_called_once_with("", "")
    assert ctx.stream is gen


def test_from_llm_stream_sets_stream_and_clears_output():
    ctx = SimpleNamespace(set_output=Mock(), stream=None)
    response = SimpleNamespace(delta="chunk")
    r = Response()
    r.from_llm_stream(ctx, model=Mock(), llm=Mock(), response=response)
    ctx.set_output.assert_called_once_with("", "")
    assert ctx.stream is response