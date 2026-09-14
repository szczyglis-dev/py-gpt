#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.cmd_files import Plugin
from pygpt_net.plugin.cmd_files.worker import Worker


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "cmd.read_file" in options
    assert "cmd.save_file" in options
    assert "cmd.append_file" in options
    assert "cmd.delete_file" in options
    assert "cmd.list_dir" in options
    assert "cmd.mkdir" in options
    assert "cmd.download_file" in options
    assert "cmd.rmdir" in options
    assert "cmd.copy_file" in options
    assert "cmd.copy_dir" in options
    assert "cmd.move" in options
    assert "cmd.is_dir" in options
    assert "cmd.is_file" in options
    assert "cmd.file_exists" in options
    assert "cmd.file_size" in options
    assert "cmd.file_info" in options


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
    assert len(event.data["cmd"]) == 24


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


def test_project_index_option_defaults_to_enabled(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    assert plugin.get_option_value("use_project_index") is True


def test_get_index_name_prefers_current_project(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.set_option_value("use_project_index", True)
    plugin.set_option_value("idx", "base")
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value="__project__")

    assert plugin.get_index_name() == "__project__"


def test_get_index_name_falls_back_to_configured_global_index(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.set_option_value("use_project_index", True)
    plugin.set_option_value("idx", "docs")
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value=None)

    assert plugin.get_index_name() == "docs"


def test_get_index_name_can_disable_project_override(mock_window):
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.set_option_value("use_project_index", False)
    plugin.set_option_value("idx", "docs")
    mock_window.core.idx.get_current_project_idx = MagicMock(return_value="__project__")

    assert plugin.get_index_name() == "docs"
    mock_window.core.idx.get_current_project_idx.assert_not_called()


def test_tool_response_request_preserves_list_path_type():
    """The request echoed with a tool result must keep JSON-native types."""
    worker = Worker()
    response = worker.make_response(
        {
            "cmd": "read_file",
            "params": {
                "path": ["/tmp/a.txt", "/tmp/b.txt"],
            },
        },
        result=[],
    )

    assert response["request"] == {
        "cmd": "read_file",
        "path": ["/tmp/a.txt", "/tmp/b.txt"],
    }
    assert isinstance(response["request"]["path"], list)


def test_tool_response_request_keeps_string_query_as_string():
    """JSON-looking text is still text; only its original type is preserved."""
    worker = Worker()
    request = worker.from_request({
        "cmd": "query_file",
        "params": {
            "path": "/tmp/a.txt",
            "query": '{"question": "content?"}',
        },
    })

    assert request["path"] == "/tmp/a.txt"
    assert request["query"] == '{"question": "content?"}'
    assert isinstance(request["query"], str)


def test_tool_response_request_falls_back_for_non_json_value():
    """Non-JSON internal values keep the legacy string fallback."""
    from pathlib import Path

    worker = Worker()
    request = worker.from_request({
        "cmd": "read_file",
        "params": {
            "path": Path("/tmp/a.txt"),
        },
    })

    assert request["path"] == "/tmp/a.txt"
    assert isinstance(request["path"], str)

