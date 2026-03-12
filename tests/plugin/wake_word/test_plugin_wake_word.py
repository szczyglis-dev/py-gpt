#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.plugin.wake_word import Plugin


def test_options(mock_window):
    """Test plugin options are correctly initialized"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "wake_word_model" in options
    assert "custom_model_path" in options
    assert "threshold" in options
    assert "cooldown_seconds" in options
    assert "audio_feedback" in options
    assert "auto_enable_audio_input" in options


def test_plugin_id(mock_window):
    """Test plugin id and name"""
    plugin = Plugin(window=mock_window)
    assert plugin.id == "wake_word"
    assert plugin.name == "Wake Word"
    assert "audio.control" in plugin.type


def test_default_threshold(mock_window):
    """Test default threshold value"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    threshold = plugin.get_option_value("threshold")
    assert threshold == 0.5


def test_default_cooldown(mock_window):
    """Test default cooldown value"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    cooldown = plugin.get_option_value("cooldown_seconds")
    assert cooldown == 3


def test_default_model(mock_window):
    """Test default wake word model"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    model = plugin.get_option_value("wake_word_model")
    assert model == "hey_jarvis"


def test_handle_enable(mock_window):
    """Test plugin enable triggers audio input and listener"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    # Mock start_listener to prevent actual thread creation
    plugin.start_listener = MagicMock()

    event = Event()
    event.name = Event.ENABLE
    event.data = {"value": "wake_word"}
    event.ctx = None
    plugin.handle(event)

    # Should enable audio_input plugin
    mock_window.controller.plugins.enable.assert_called_with("audio_input")
    # Should start listener
    plugin.start_listener.assert_called_once()


def test_handle_disable(mock_window):
    """Test plugin disable stops listener"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    plugin.listening = True
    plugin.stop_listener = MagicMock()

    event = Event()
    event.name = Event.DISABLE
    event.data = {"value": "wake_word"}
    event.ctx = None
    plugin.handle(event)

    plugin.stop_listener.assert_called_once()


def test_handle_enable_other_plugin(mock_window):
    """Test that enabling another plugin does not trigger wake word"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.start_listener = MagicMock()

    event = Event()
    event.name = Event.ENABLE
    event.data = {"value": "some_other_plugin"}
    event.ctx = None
    plugin.handle(event)

    plugin.start_listener.assert_not_called()


def test_trigger_audio_input_simple(mock_window):
    """Test trigger_audio_input in simple mode"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    audio_input_mock = MagicMock()
    audio_input_mock.enabled = True
    audio_input_mock.is_advanced.return_value = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    plugin.trigger_audio_input()

    audio_input_mock.toggle_recording_simple.assert_called_once_with(state=True, auto=True)


def test_trigger_audio_input_advanced(mock_window):
    """Test trigger_audio_input in advanced mode"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    audio_input_mock = MagicMock()
    audio_input_mock.enabled = True
    audio_input_mock.is_advanced.return_value = True
    audio_input_mock.speech_enabled = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    plugin.trigger_audio_input()

    assert audio_input_mock.magic_word_detected is True
    audio_input_mock.toggle_speech.assert_called_once_with(True)


def test_trigger_audio_input_disabled(mock_window):
    """Test trigger_audio_input when audio input is disabled"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    audio_input_mock = MagicMock()
    audio_input_mock.enabled = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    # Should not raise, just log
    plugin.trigger_audio_input()
    audio_input_mock.toggle_recording_simple.assert_not_called()


def test_destroy(mock_window):
    """Test destroy stops listener"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.listening = True

    plugin.destroy()

    assert plugin.listening is False
