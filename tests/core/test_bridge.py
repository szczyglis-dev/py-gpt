#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.31 20:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.core.bridge import Bridge


def test_call_chat(mock_window):
    """Test call"""
    mock_window.core.gpt.call = MagicMock(return_value=True)
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="chat", model=None)
    mock_window.core.gpt.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_completion(mock_window):
    """Test call"""
    mock_window.core.gpt.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="completion")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="completion", model=None)
    mock_window.core.gpt.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_vision(mock_window):
    """Test call"""
    mock_window.core.gpt.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="vision")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="vision", model=None)
    mock_window.core.gpt.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_img(mock_window):
    """Test call"""
    mock_window.core.gpt.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="img")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="img", model=None)
    mock_window.core.gpt.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_langchain(mock_window):
    """Test call"""
    mock_window.core.chain.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="langchain")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="langchain", model=None)
    mock_window.core.chain.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_llama_index(mock_window):
    """Test call"""
    mock_window.core.idx = MagicMock()
    mock_window.core.idx.chat.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="llama_index")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="llama_index", model=None)
    mock_window.core.idx.chat.call.assert_called_once()
    mock_window.controller.mode.switch_inline.assert_called_once()


def test_call_agent_chat(mock_window):
    """Test call"""
    mock_window.core.gpt.call = MagicMock(return_value=True)
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="agent", model=None)
    mock_window.core.gpt.call.assert_called_once()


def test_call_agent_llama_index(mock_window):
    """Test call"""
    mock_window.core.config.set("agent.mode", "llama_index")
    mock_window.core.idx.chat.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="llama_index")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="agent", model=None)
    mock_window.core.idx.chat.call.assert_called_once()


def test_call_agent_langchain(mock_window):
    """Test call"""
    mock_window.core.config.set("agent.mode", "langchain")
    mock_window.core.chain.call = MagicMock(return_value=True)
    mock_window.controller.mode.switch_inline = MagicMock(return_value="langchain")
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.call(ctx=ctx, prompt="test", mode="agent", model=None)
    mock_window.core.chain.call.assert_called_once()


def test_quick_call(mock_window):
    """Test quick call"""
    mock_window.core.gpt.quick_call = MagicMock(return_value=True)
    bridge = Bridge(mock_window)
    ctx = CtxItem()
    bridge.quick_call(ctx=ctx, prompt="test", mode="chat", model=None)
    mock_window.core.gpt.quick_call.assert_called_once()
