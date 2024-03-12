#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_code_interpreter import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "python_cmd_tpl" in options
    assert "cmd.code_execute" in options
    assert "cmd.code_execute_file" in options
    assert "cmd.sys_exec" in options
    assert "sandbox_docker" in options
    assert "sandbox_docker_image" in options


def test_handle_cmd_syntax(mock_window):
    """Test handle event: cmd.syntax"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.syntax"
    event.data = {
        "cmd": []
    }
    event.ctx = ctx
    plugin.handle(event)
    assert len(event.data["cmd"]) == 0  # code_execute, code_execute_file, sys_exec


def test_handle_cmd_execute_code_execute(mock_window):
    """Test handle event: cmd.execute"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "code_execute",
                "params": {
                    "filename": "test.py",
                    "code": "print('test')",
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()


def test_handle_cmd_execute_sys_exec(mock_window):
    """Test handle event: cmd.execute"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "sys_exec",
                "params": {
                    "command": "echo test",
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()