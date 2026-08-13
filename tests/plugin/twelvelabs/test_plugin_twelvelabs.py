#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Mohit Varikuti                       #
# Updated Date: 2026.06.25 00:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.twelvelabs import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "api_key" in options
    assert "pegasus_model" in options
    assert "marengo_model" in options
    assert "max_tokens" in options
    assert "temperature" in options
    assert "timeout" in options
    # API key option must be marked as secret
    assert options["api_key"]["secret"] is True


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
    assert len(event.data["cmd"]) == 2  # tl_analyze_video, tl_embed_text


def test_handle_cmd_execute(mock_window):
    """Test handle event: cmd.execute dispatches to the worker thread pool"""
    mock_window.threadpool = MagicMock()
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    event = Event()
    event.name = "cmd.execute"
    event.data = {
        "commands": [
            {
                "cmd": "tl_embed_text",
                "params": {
                    "text": "a cat playing piano"
                }
            }
        ]
    }
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()


def test_embed_text_missing_key(mock_window):
    """Worker should fail clearly when no API key is configured"""
    from pygpt_net.plugin.twelvelabs.worker import Worker

    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.options["api_key"]["value"] = ""

    worker = Worker()
    worker.from_defaults(plugin)
    # ensure env var does not leak a key into the test
    old = os.environ.pop("TWELVELABS_API_KEY", None)
    try:
        with pytest.raises(RuntimeError):
            worker.get_client()
    finally:
        if old is not None:
            os.environ["TWELVELABS_API_KEY"] = old


@pytest.mark.skipif(
    not os.environ.get("TWELVELABS_API_KEY"),
    reason="requires TWELVELABS_API_KEY for a live TwelveLabs API call",
)
def test_embed_text_live(mock_window):
    """Live smoke test: Marengo returns a 512-dim text embedding"""
    from pygpt_net.plugin.twelvelabs.worker import Worker

    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    worker = Worker()
    worker.from_defaults(plugin)
    item = {"cmd": "tl_embed_text", "params": {"text": "a cat playing piano"}}
    response = worker.cmd_tl_embed_text(item)
    result = response["result"]
    assert result["dimensions"] == 512
    assert len(result["embedding"]) == 512
