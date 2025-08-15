#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_code_interpreter import Plugin
from pygpt_net.plugin.cmd_code_interpreter.worker import Worker

def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "python_cmd_tpl" in options
    assert "cmd.code_execute" in options
    assert "cmd.code_execute_file" in options
    assert "sandbox_docker" in options
    assert "sandbox_ipython" in options


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
    assert len(event.data["cmd"]) == 7  # code_execute, code_execute_file, sys_exec

