#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.03 22:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_files import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "cmd_read_file" in options
    assert "cmd_save_file" in options
    assert "cmd_append_file" in options
    assert "cmd_delete_file" in options
    assert "cmd_list_dir" in options
    assert "cmd_mkdir" in options
    assert "cmd_download_file" in options
    assert "cmd_rmdir" in options
    assert "cmd_copy_file" in options
    assert "cmd_copy_dir" in options
    assert "cmd_move" in options
    assert "cmd_is_dir" in options
    assert "cmd_is_file" in options
    assert "cmd_file_exists" in options
    assert "cmd_file_size" in options
    assert "cmd_file_info" in options
    assert "syntax_read_file" in options
    assert "syntax_save_file" in options
    assert "syntax_append_file" in options
    assert "syntax_delete_file" in options
    assert "syntax_list_dir" in options
    assert "syntax_mkdir" in options
    assert "syntax_download_file" in options
    assert "syntax_rmdir" in options
    assert "syntax_copy_file" in options
    assert "syntax_copy_dir" in options
    assert "syntax_move" in options
    assert "syntax_is_dir" in options
    assert "syntax_is_file" in options
    assert "syntax_file_exists" in options
    assert "syntax_file_size" in options
    assert "syntax_file_info" in options


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
    plugin.handle(event)
    assert len(event.data["syntax"]) == 20  # 20 commands


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
                "cmd": "read_file",
                "params": {
                    "filename": "test.txt",
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()
