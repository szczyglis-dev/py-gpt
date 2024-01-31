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
from unittest.mock import MagicMock, patch

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.self_loop import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "iterations" in options
    assert "reverse_roles" in options


def test_handle_user_send(mock_window):
    """Test handle event: user.send"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.agent.flow.on_user_send = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "user.send"
    event.data = {
        "value": ""
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.controller.agent.flow.on_user_send.assert_called_once()


def test_handle_ctx_end(mock_window):
    """Test handle event: ctx.end"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.agent.flow.on_ctx_end = MagicMock()
    mock_window.controller.chat.input.send = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "ctx.end"
    event.data = {}
    event.ctx = ctx
    plugin.options["iterations"]["value"] = 1
    plugin.handle(event)
    mock_window.controller.agent.flow.on_ctx_end.assert_called_once()


def test_handle_ctx_before(mock_window):
    """Test handle event: ctx.before"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.agent.flow.on_ctx_before = MagicMock()
    mock_window.controller.chat.input.send = MagicMock()
    ctx = CtxItem()
    ctx.input_name = "input name"
    ctx.input = "input"
    ctx.output_name = "output name"
    ctx.output = "output"
    event = Event()
    event.name = "ctx.before"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    mock_window.controller.agent.flow.on_ctx_before.assert_called_once()


def test_handle_ctx_after(mock_window):
    """Test handle event: ctx.after"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.input.send = MagicMock()
    mock_window.controller.agent.flow.on_ctx_after = MagicMock()
    ctx = CtxItem()
    ctx.output = "output"
    event = Event()
    event.name = "ctx.after"
    event.data = {}
    event.ctx = ctx
    plugin.prev_output = ""
    plugin.handle(event)
    mock_window.controller.agent.flow.on_ctx_after.assert_called_once()

