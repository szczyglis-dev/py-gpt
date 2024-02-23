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
from pygpt_net.plugin.audio_input import Plugin


def test_options(mock_window):
    """Test options"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    # assert "whisper_model" in options
    assert "timeout" in options
    assert "phrase_length" in options
    assert "min_energy" in options
    assert "adjust_noise" in options
    assert "continuous_listen" in options
    assert "auto_send" in options
    assert "wait_response" in options
    assert "magic_word" in options
    assert "magic_word_reset" in options
    assert "magic_words" in options
    assert "magic_word_timeout" in options
    assert "magic_word_phrase_length" in options
    assert "prefix_words" in options
    assert "stop_words" in options
    assert "recognition_energy_threshold" in options
    assert "recognition_dynamic_energy_threshold" in options
    assert "recognition_dynamic_energy_adjustment_damping" in options
    assert "recognition_pause_threshold" in options
    assert "recognition_adjust_for_ambient_noise_duration" in options


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


def test_handle_ctx_begin(mock_window):
    """Test handle event: ctx.begin"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "ctx.begin"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.waiting is True


def test_handle_ctx_end(mock_window):
    """Test handle event: ctx.end"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "ctx.end"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.waiting is False


def test_handle_enable(mock_window):
    """Test handle event: enable"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.handle_thread = MagicMock()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "enable"
    event.data = {
        "value": plugin.id
    }
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.speech_enabled is True
    plugin.handle_thread.assert_called_once()


def test_handle_disable(mock_window):
    """Test handle event: disable"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    mock_window.ui.plugin_addon['audio.input'].btn_toggle = MagicMock()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "disable"
    event.data = {
        "value": plugin.id
    }
    event.ctx = ctx
    plugin.handle(event)
    assert plugin.speech_enabled is False
    assert plugin.listening is False
    assert plugin.stop is True
    mock_window.ui.plugin_addon['audio.input'].btn_toggle.setChecked.assert_called_once_with(False)


def test_handle_toggle_on(mock_window):
    """Test handle event: audio.input.toggle"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.handle_thread = MagicMock()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "audio.input.toggle"
    event.data = {
        "value": True
    }
    event.ctx = ctx
    plugin.handle(event)

    assert plugin.speech_enabled is True
    assert plugin.listening is True
    assert plugin.stop is False
    plugin.handle_thread.assert_called_once()


def test_handle_toggle_off(mock_window):
    """Test handle event: audio.input.toggle"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.handle_thread = MagicMock()
    ctx = CtxItem()
    ctx.output = "output text"
    event = Event()
    event.name = "audio.input.toggle"
    event.data = {
        "value": False
    }
    event.ctx = ctx
    plugin.handle(event)

    assert plugin.listening is False


def test_handle_audio_stop(mock_window):
    """Test handle event: audio.input.stop"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.on_stop = MagicMock()
    ctx = CtxItem()
    event = Event()
    event.name = "audio.input.stop"
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)
    plugin.on_stop.assert_called_once()
