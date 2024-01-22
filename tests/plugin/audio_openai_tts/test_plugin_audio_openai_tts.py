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
from pygpt_net.plugin.audio_openai_tts import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "model" in options
    assert "voice" in options


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


def test_handle_ctx_after(mock_window):
    """Test handle event: ctx.after"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.threadpool.start = MagicMock()
    mock_window.core.audio.clean_text = MagicMock(return_value="cleaned text")
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "ctx.after"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()


def test_handle_read_text(mock_window):
    """Test handle event: audio.read_text"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.threadpool.start = MagicMock()
    mock_window.core.audio.clean_text = MagicMock(return_value="cleaned text")
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "audio.read_text"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    mock_window.threadpool.start.assert_called_once()


def test_handle_audio_stop(mock_window):
    """Test handle event: audio.output.stop"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.stop_audio = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "audio.output.stop"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    plugin.stop_audio.assert_called_once()
