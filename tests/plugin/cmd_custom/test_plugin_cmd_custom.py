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
from pygpt_net.plugin.cmd_custom import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "cmds" in options


def test_handle_cmd_syntax(mock_window):
    """Test handle event: cmd.syntax"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.syntax"
    event.data = {
        "syntax": []
    }
    event.ctx = ctx
    cmds = [
        {
            "name": "example_cmd",
            "instruction": "execute tutorial test command",
            "params": "hello, world",
        }
    ]
    plugin.options["cmds"]["value"] = cmds
    plugin.handle(event)
    assert len(event.data["syntax"]) == 1


def test_handle_cmd_execute(mock_window):
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
                "cmd": "example_cmd",
                "params": {
                    "hello": "hi",
                    "world": "earth",
                }
            }
        ]
    }
    event.ctx = ctx
    cmds = [
        {
            "name": "example_cmd",
            "instruction": "execute tutorial test command",
            "params": "hello, world",
        }
    ]
    plugin.options["cmds"]["value"] = cmds
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()
