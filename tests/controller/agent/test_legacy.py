#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.agent.legacy import Legacy

def test_setup(mock_window):
    """Test setup"""
    legacy = Legacy(mock_window)
    mock_window.ui.add_hook = MagicMock()
    legacy.setup()
    mock_window.ui.add_hook.assert_called()


def test_hook_update(mock_window):
    """Test hook_update"""
    legacy = Legacy(mock_window)
    legacy.update = MagicMock()
    legacy.hook_update("agent.iterations", 3, None)
    legacy.update.assert_called_once()


def test_is_inline(mock_window):
    """Test is_inline"""
    legacy = Legacy(mock_window)
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=True)
    assert legacy.is_inline() is True
    mock_window.controller.plugins.is_type_enabled = MagicMock(return_value=False)
    assert legacy.is_inline() is False

def test_update(mock_window):
    """Test update"""
    legacy = Legacy(mock_window)
    mock_window.controller.agent.common = MagicMock()
    mock_window.controller.agent.common.toggle_status = MagicMock()
    legacy.update()
    mock_window.controller.agent.common.toggle_status.assert_called_once()


def test_on_system_prompt(mock_window):
    """Test on system prompt"""
    legacy = Legacy(mock_window)
    legacy.window.core.command.is_native_enabled = MagicMock(return_value=False)
    result = legacy.on_system_prompt("prompt", "append_prompt", True)
    assert result.startswith("prompt\nappend_prompt\n\nSTATUS UPDATE:")


def test_on_input_before(mock_window):
    """Test on input before"""
    legacy = Legacy(mock_window)
    result = legacy.on_input_before("prompt")
    assert result == "user: prompt"


def test_on_user_send(mock_window):
    """Test on user send"""
    mock_window.controller.agent.legacy.update = MagicMock()
    legacy = Legacy(mock_window)
    legacy.on_user_send("text")
    assert legacy.iteration == 0
    assert legacy.prev_output is None
    assert legacy.is_user is True
    assert legacy.stop is False
    assert mock_window.controller.agent.legacy.update.called


def test_on_ctx_end(mock_window):
    """Test on ctx end"""
    ctx = CtxItem()
    mock_window.controller.agent.legacy.update = MagicMock()
    legacy = Legacy(mock_window)
    iterations = 2
    legacy.on_ctx_end(ctx, iterations=iterations)
    assert legacy.iteration == 1
    assert legacy.stop is False
    assert mock_window.controller.agent.legacy.update.called


def test_on_ctx_end_stop(mock_window):
    """Test on ctx end"""
    ctx = CtxItem()
    mock_window.controller.agent.update = MagicMock()
    legacy = Legacy(mock_window)
    legacy.stop = True
    iterations = 2
    legacy.prev_output = "output"
    legacy.on_ctx_end(ctx, iterations=iterations)
    assert legacy.iteration == 0
    assert legacy.stop is False
    assert legacy.prev_output is None
    # assert mock_window.controller.agent.update.called


def test_on_ctx_before(mock_window):
    """Test on ctx before"""
    ctx = CtxItem()
    legacy = Legacy(mock_window)
    legacy.on_ctx_before(ctx)
    assert legacy.iteration == 0
    assert legacy.stop is False
    assert legacy.prev_output is None
    assert legacy.is_user is False
    assert ctx.internal is True


def test_on_ctx_after(mock_window):
    """Test on ctx after"""
    mock_window.core.prompt.get = MagicMock(return_value="continue...")
    ctx = CtxItem()
    ctx.output = "output"
    legacy = Legacy(mock_window)
    legacy.on_ctx_after(ctx)
    assert legacy.prev_output == "continue..."


def test_on_cmd(mock_window):
    """Test on cmd"""
    mock_window.core.config.set('agent.auto_stop', True)
    ctx = CtxItem()
    ctx.output = "output"
    legacy = Legacy(mock_window)
    legacy.on_cmd(ctx, [{"cmd": "goal_update", "params": {"status": "finished"}}])
    assert legacy.stop is True
    assert legacy.prev_output is None
    assert legacy.iteration == 0
    assert legacy.is_user is True


def test_cmd(mock_window):
    """Test cmd"""
    mock_window.core.config.set('agent.auto_stop', True)
    ctx = CtxItem()
    ctx.output = "output"
    legacy = Legacy(mock_window)
    legacy.cmd(ctx, [{"cmd": "goal_update", "params": {"status": "finished"}}])
    assert legacy.stop is True
    assert legacy.prev_output is None
    assert legacy.iteration == 0
    assert legacy.is_user is True


def test_on_stop(mock_window):
    """Test on stop"""
    legacy = Legacy(mock_window)
    legacy.on_stop()
    assert legacy.stop is True
    assert legacy.prev_output is None
    assert legacy.iteration == 0
    assert legacy.is_user is True
