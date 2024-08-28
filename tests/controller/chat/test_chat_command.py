#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.chat.command import Command
from pygpt_net.item.ctx import CtxItem


def test_handle_cmd(mock_window):
    """Test handle cmd: all commands"""
    command = Command(mock_window)
    mock_window.core.config.data['cmd'] = True  # enable all cmd execution
    mock_window.controller.plugins.apply_cmds = MagicMock()
    mock_window.controller.plugins.apply_cmds_inline = MagicMock()
    mock_window.ui.status = MagicMock()
    cmds = [
        {'cmd': 'cmd1', 'params': {'param1': 'value1'}},
        {'cmd': 'cmd2', 'params': {'param2': 'value2'}},
    ]
    mock_window.core.command.extract_cmds = MagicMock(return_value=cmds)
    mock_window.controller.agent.experts.enabled = MagicMock(return_value=False)

    ctx = CtxItem()
    command.handle(ctx)

    mock_window.controller.plugins.apply_cmds.assert_called_once()
    mock_window.controller.plugins.apply_cmds_inline.assert_not_called()
    mock_window.ui.status.assert_called_once()


def test_handle_cmd_only(mock_window):
    """Test handle cmd: only inline commands"""
    command = Command(mock_window)
    mock_window.core.config.data['cmd'] = False  # disable cmd execution, allow only 'inline' commands
    mock_window.controller.plugins.apply_cmds = MagicMock()
    mock_window.controller.plugins.apply_cmds_inline = MagicMock()
    mock_window.ui.status = MagicMock()
    cmds = [
        {'cmd': 'cmd1', 'params': {'param1': 'value1'}},
        {'cmd': 'cmd2', 'params': {'param2': 'value2'}},
    ]
    mock_window.core.command.extract_cmds = MagicMock(return_value=cmds)
    mock_window.controller.agent.experts.enabled = MagicMock(return_value=False)

    ctx = CtxItem()
    command.handle(ctx)

    mock_window.controller.plugins.apply_cmds_inline.assert_called_once()
    mock_window.controller.plugins.apply_cmds.assert_not_called()


def test_handle_cmd_no_cmds(mock_window):
    """Test handle cmd: empty commands"""
    command = Command(mock_window)
    mock_window.core.config.data['cmd'] = True  # enable all cmd execution
    mock_window.controller.plugins.apply_cmds = MagicMock()
    mock_window.controller.plugins.apply_cmds_inline = MagicMock()
    mock_window.ui.status = MagicMock()

    cmds = []
    mock_window.core.command.extract_cmds = MagicMock(return_value=cmds)

    ctx = CtxItem()
    command.handle(ctx)

    mock_window.controller.plugins.apply_cmds.assert_not_called()
    mock_window.controller.plugins.apply_cmds_inline.assert_not_called()
    mock_window.ui.status.assert_not_called()
