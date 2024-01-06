#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 05:00:00                  #
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
    ctx = CtxItem()
    event = Event()
    event.name = "user.send"
    event.data = {
        "value": ""
    }
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.iteration == 0
    assert plugin.prev_output is None


def test_handle_ctx_end(mock_window):
    """Test handle event: ctx.end"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.input.send = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "ctx.end"
    event.data = {}
    event.ctx = ctx
    plugin.iteration = 0
    plugin.prev_output = "prev output"
    plugin.options["iterations"]["value"] = 1
    plugin.handle(event)
    mock_window.controller.chat.input.send.assert_called_once_with("prev output", force=True, internal=True)


def test_handle_ctx_before(mock_window):
    """Test handle event: ctx.before"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
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
    plugin.iteration = 1
    plugin.prev_output = "prev output"
    plugin.options["reverse_roles"]["value"] = True
    plugin.options["iterations"]["value"] = 3
    plugin.handle(event)
    assert ctx.input_name == "output name"
    assert ctx.output_name == "input name"


def test_handle_ctx_after(mock_window):
    """Test handle event: ctx.after"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.controller.chat.input.send = MagicMock()
    ctx = CtxItem()
    ctx.output = "output"
    event = Event()
    event.name = "ctx.after"
    event.data = {}
    event.ctx = ctx
    plugin.iteration = 1
    plugin.prev_output = ""
    plugin.handle(event)
    assert plugin.prev_output == "output"

