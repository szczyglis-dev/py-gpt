#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 15:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.core.idx import Chat


def test_call(mock_window):
    """Test call"""
    chat = Chat(mock_window)
    chat.chat = MagicMock(return_value=True)
    chat.query = MagicMock(return_value=True)
    model = ModelItem()
    model.llama_index = {"mode": ["chat"]}
    ctx = CtxItem()
    idx = "test"
    sys_prompt = "test"
    stream = True
    bridge_context = BridgeContext(
        ctx=ctx,
        idx=idx,
        model=model,
        system_prompt=sys_prompt,
        stream=stream,
    )
    extra = {}
    chat.call(
        context=bridge_context,
        extra=extra,
    )
    chat.chat.assert_called_once_with(
        context=bridge_context,
        extra=extra,
    )


def test_raw_query(mock_window):
    """Test raw query"""
    chat = Chat(mock_window)
    chat.query = MagicMock(return_value=True)
    model = ModelItem()
    ctx = CtxItem()
    idx = "test"
    sys_prompt = "test"
    stream = True
    bridge_context = BridgeContext(
        ctx=ctx,
        idx=idx,
        model=model,
        system_prompt=sys_prompt,
        stream=stream,
    )
    extra = {}
    chat.raw_query(
        context=bridge_context,
        extra=extra,
    )
    chat.query.assert_called_once_with(
        context=bridge_context,
        extra=extra,
    )


def test_query(mock_window):
    """Test query"""
    response = MagicMock()
    response.response = MagicMock(return_value="response")
    response.query = MagicMock(return_value=response)
    index = MagicMock()
    index.as_query_engine = MagicMock(return_value=response)
    chat = Chat(mock_window)
    chat.get_custom_prompt = MagicMock(return_value=None)
    mock_window.core.config.set("llama.log", False)
    mock_window.core.tokens.from_llama_messages = MagicMock(return_value=222)
    service_context = MagicMock()
    mock_window.core.idx.llm.get_service_context = MagicMock(return_value=service_context)
    chat.storage = MagicMock()
    chat.storage.exists = MagicMock(return_value=True)
    chat.storage.get = MagicMock(return_value=index)
    ctx = CtxItem()
    ctx.input = "test"
    model = ModelItem()
    bridge_context = BridgeContext(
        ctx=ctx,
        idx=index,
        model=model,
        system_prompt_raw="test",
        stream=False,
    )
    extra = {}
    chat.query(
        context=bridge_context,
        extra=extra,
    )
    chat.get_custom_prompt.assert_called_once_with("test")
    assert ctx.input_tokens == 222
    assert ctx.output == str(response.response)


def test_chat(mock_window):
    """Test chat"""
    response = MagicMock()
    response.response = MagicMock(return_value="response")
    chat_engine = MagicMock()
    chat_engine.chat = MagicMock(return_value=response)
    index = MagicMock()
    index.as_chat_engine = MagicMock(return_value=chat_engine)
    chat = Chat(mock_window)
    chat.get_custom_prompt = MagicMock(return_value=None)
    mock_window.core.config.set("llama.log", False)
    mock_window.core.config.set("max_total_tokens", 11111)
    mock_window.core.models.get_num_ctx = MagicMock(return_value=4096)
    mock_window.core.tokens.from_llama_messages = MagicMock(return_value=222)
    service_context = MagicMock()
    mock_window.core.idx.llm.get_service_context = MagicMock(return_value=service_context)
    chat.storage = MagicMock()
    chat.storage.exists = MagicMock(return_value=True)
    chat.storage.get = MagicMock(return_value=index)
    ctx = CtxItem()
    ctx.input = "test"
    model = ModelItem()
    chat.get_memory_buffer = MagicMock(return_value=None)
    bridge_context = BridgeContext(
        ctx=ctx,
        idx=index,
        model=model,
        system_prompt="test",
        stream=False,
    )
    extra = {}
    chat.chat(
        context=bridge_context,
        extra=extra,
    )
    assert ctx.input_tokens == 222
    assert ctx.output == str(response.response)


def test_get_custom_prompt(mock_window):
    """Test get custom prompt"""
    chat = Chat(mock_window)
    custom = chat.get_custom_prompt("test")
    assert custom is not None
