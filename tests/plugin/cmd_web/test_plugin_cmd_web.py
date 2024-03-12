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
from pygpt_net.plugin.cmd_web import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    # assert "google_api_key" in options
    # assert "google_api_cx" in options
    assert "num_pages" in options
    assert "max_page_content_length" in options
    assert "chunk_size" in options
    assert "disable_ssl" in options
    assert "max_result_length" in options
    assert "summary_max_tokens" in options
    assert "summary_model" in options
    assert "prompt_summarize" in options
    assert "prompt_summarize_url" in options


def test_handle_input_before(mock_window):
    """Test handle event: input.before"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "input.before"
    event.data = {
        "value": "user input"
    }
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.input_text == "user input"


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
    assert len(event.data["cmd"]) == 6  # web_search, web_url_open


def test_handle_cmd_execute_web_search(mock_window):
    """Test handle event: cmd.execute"""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    provider.name = "Google Custom Search"
    providers = {
        "google_custom_search": provider,
    }
    plugin.get_providers = MagicMock(return_value=providers)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "web_search",
                "params": {
                    "query": "test query"
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.options["google_api_key"] = {}
    plugin.options["google_api_cx"] = {}
    plugin.options["google_api_key"]["value"] = "API KEY"
    plugin.options["google_api_cx"]["value"] = "API CX"
    plugin.handle(event)

    mock_window.threadpool.start.assert_called_once()


def test_handle_cmd_execute_web_url_open(mock_window):
    """Test handle event: cmd.execute"""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    provider.name = "Google Custom Search"
    providers = {
        "google_custom_search": provider,
    }
    plugin.get_providers = MagicMock(return_value=providers)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "web_url_open",
                "params": {
                    "query": "https://pygpt.net"
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)

    mock_window.threadpool.start.assert_called_once()
