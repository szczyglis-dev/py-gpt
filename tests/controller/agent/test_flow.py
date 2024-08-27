#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 05:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.agent.flow import Flow


def test_on_system_prompt(mock_window):
    """Test on system prompt"""
    flow = Flow(mock_window)
    flow.window.core.command.is_native_enabled = MagicMock(return_value=False)
    result = flow.on_system_prompt("prompt", "append_prompt", True)
    assert result.startswith("prompt\nappend_prompt\n\nSTATUS UPDATE:")


def test_on_input_before(mock_window):
    """Test on input before"""
    flow = Flow(mock_window)
    result = flow.on_input_before("prompt")
    assert result == "user: prompt"


def test_on_user_send(mock_window):
    """Test on user send"""
    mock_window.controller.agent.update = MagicMock()
    flow = Flow(mock_window)
    flow.on_user_send("text")
    assert flow.iteration == 0
    assert flow.prev_output is None
    assert flow.is_user is True
    assert flow.stop is False
    assert mock_window.controller.agent.update.called


def test_on_ctx_end(mock_window):
    """Test on ctx end"""
    ctx = CtxItem()
    mock_window.controller.agent.update = MagicMock()
    flow = Flow(mock_window)
    iterations = 2
    flow.on_ctx_end(ctx, iterations=iterations)
    assert flow.iteration == 1
    assert flow.stop is False
    assert mock_window.controller.agent.update.called


def test_on_ctx_end_stop(mock_window):
    """Test on ctx end"""
    ctx = CtxItem()
    mock_window.controller.agent.update = MagicMock()
    flow = Flow(mock_window)
    flow.stop = True
    iterations = 2
    flow.prev_output = "output"
    flow.on_ctx_end(ctx, iterations=iterations)
    assert flow.iteration == 0
    assert flow.stop is False
    assert flow.prev_output is None
    # assert mock_window.controller.agent.update.called


def test_on_ctx_before(mock_window):
    """Test on ctx before"""
    ctx = CtxItem()
    flow = Flow(mock_window)
    flow.on_ctx_before(ctx)
    assert flow.iteration == 0
    assert flow.stop is False
    assert flow.prev_output is None
    assert flow.is_user is False
    assert ctx.internal is True


def test_on_ctx_after(mock_window):
    """Test on ctx after"""
    mock_window.core.prompt.get = MagicMock(return_value="continue...")
    ctx = CtxItem()
    ctx.output = "output"
    flow = Flow(mock_window)
    flow.on_ctx_after(ctx)
    assert flow.prev_output == "continue..."


def test_on_cmd(mock_window):
    """Test on cmd"""
    mock_window.core.config.set('agent.auto_stop', True)
    ctx = CtxItem()
    ctx.output = "output"
    flow = Flow(mock_window)
    flow.on_cmd(ctx, [{"cmd": "goal_update", "params": {"status": "finished"}}])
    assert flow.stop is True
    assert flow.prev_output is None
    assert flow.iteration == 0
    assert flow.is_user is True
    assert flow.window.ui.status.called


def test_cmd(mock_window):
    """Test cmd"""
    mock_window.core.config.set('agent.auto_stop', True)
    ctx = CtxItem()
    ctx.output = "output"
    flow = Flow(mock_window)
    flow.cmd(ctx, [{"cmd": "goal_update", "params": {"status": "finished"}}])
    assert flow.stop is True
    assert flow.prev_output is None
    assert flow.iteration == 0
    assert flow.is_user is True
    assert flow.window.ui.status.called


def test_on_stop(mock_window):
    """Test on stop"""
    flow = Flow(mock_window)
    flow.on_stop()
    assert flow.stop is True
    assert flow.prev_output is None
    assert flow.iteration == 0
    assert flow.is_user is True
