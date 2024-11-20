#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.12 14:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.openai_dalle import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "prompt" in options


def test_handle_cmd_execute(mock_window):
    """Test handle event: cmd.execute"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.core.bridge.generate = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "image",
                "params": {
                    "query": "test query"
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)


def test_handle_cmd_inline(mock_window):
    """Test handle event: cmd.inline"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.core.bridge.call = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.inline"
    event.data = {
        "commands": [
            {
                "cmd": "image",
                "params": {
                    "query": "test query"
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)


def test_handle_sys_prompt(mock_window):
    """Test handle event: system.prompt"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.core.image.generate = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "system.prompt"
    event.data = {
        "value": "prompt"
    }
    event.ctx = ctx
    plugin.get_option_value = MagicMock(return_value="test append")
    plugin.handle(event)
    assert event.data["value"] == "prompt"
