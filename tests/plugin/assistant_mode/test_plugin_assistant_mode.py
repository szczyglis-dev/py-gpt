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
from pygpt_net.plugin.assistant_mode import Plugin


def test_options(mock_window):
    """Test plugin options are correctly initialized"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    options = plugin.setup()
    assert "auto_listen_after_response" in options
    assert "require_wake_word_each_turn" in options
    assert "conversation_timeout" in options
    assert "stop_words" in options
    assert "greeting_enabled" in options
    assert "greeting_text" in options
    assert "auto_enable_plugins" in options
    assert "response_delay" in options


def test_plugin_id(mock_window):
    """Test plugin id and name"""
    plugin = Plugin(window=mock_window)
    assert plugin.id == "assistant_mode"
    assert plugin.name == "Assistant Mode"
    assert "audio.control" in plugin.type


def test_enable_activates(mock_window):
    """Test enabling the plugin sets active state"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    # Mock plugins
    mock_window.core.plugins.get.return_value = MagicMock(enabled=False)

    event = Event()
    event.name = Event.ENABLE
    event.data = {"value": "assistant_mode"}
    event.ctx = None
    plugin.handle(event)

    assert plugin.active is True


def test_disable_deactivates(mock_window):
    """Test disabling the plugin clears active state"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.in_conversation = True

    event = Event()
    event.name = Event.DISABLE
    event.data = {"value": "assistant_mode"}
    event.ctx = None
    plugin.handle(event)

    assert plugin.active is False
    assert plugin.in_conversation is False


def test_enable_other_plugin_no_effect(mock_window):
    """Test enabling another plugin does not activate assistant mode"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()

    event = Event()
    event.name = Event.ENABLE
    event.data = {"value": "some_other_plugin"}
    event.ctx = None
    plugin.handle(event)

    assert plugin.active is False


def test_ctx_begin_sets_conversation(mock_window):
    """Test CTX_BEGIN sets in_conversation flag"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True

    ctx = CtxItem()
    event = Event()
    event.name = Event.CTX_BEGIN
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)

    assert plugin.in_conversation is True


def test_ctx_begin_inactive_no_effect(mock_window):
    """Test CTX_BEGIN has no effect when inactive"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = False

    ctx = CtxItem()
    event = Event()
    event.name = Event.CTX_BEGIN
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)

    assert plugin.in_conversation is False


def test_stop_word_detection(mock_window):
    """Test stop word detection in input"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.in_conversation = True

    event = Event()
    event.name = Event.INPUT_BEFORE
    event.data = {"value": "Goodbye!"}
    event.ctx = None
    plugin.handle(event)

    # After stop word, conversation should end
    assert plugin.in_conversation is False


def test_no_stop_word_keeps_conversation(mock_window):
    """Test normal input does not end conversation"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.in_conversation = True

    event = Event()
    event.name = Event.INPUT_BEFORE
    event.data = {"value": "What's the weather?"}
    event.ctx = None
    plugin.handle(event)

    assert plugin.in_conversation is True


def test_response_complete_with_wake_word_requirement(mock_window):
    """Test response complete when wake word required each turn"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.in_conversation = True

    # Set require wake word each turn
    plugin.options["require_wake_word_each_turn"]["value"] = True

    ctx = CtxItem()
    event = Event()
    event.name = Event.CTX_END
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)

    # Should NOT auto-listen, just wait for wake word
    assert plugin.in_conversation is False


def test_response_complete_auto_listen(mock_window):
    """Test response complete triggers auto-listen"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.in_conversation = True
    plugin.options["require_wake_word_each_turn"]["value"] = False
    plugin.options["response_delay"]["value"] = 0  # no delay for test

    # Mock audio input
    audio_input_mock = MagicMock()
    audio_input_mock.enabled = True
    audio_input_mock.is_advanced.return_value = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    # Mock start_listening to avoid QTimer
    plugin.start_listening = MagicMock()
    plugin.start_timeout_timer = MagicMock()

    ctx = CtxItem()
    event = Event()
    event.name = Event.CTX_END
    event.data = {}
    event.ctx = ctx
    plugin.handle(event)

    assert plugin.in_conversation is False
    plugin.start_listening.assert_called_once()


def test_start_listening_simple_mode(mock_window):
    """Test start_listening triggers simple mode recording"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True

    audio_input_mock = MagicMock()
    audio_input_mock.enabled = True
    audio_input_mock.is_advanced.return_value = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    plugin.start_listening()

    audio_input_mock.toggle_recording_simple.assert_called_once_with(state=True, auto=True)


def test_start_listening_advanced_mode(mock_window):
    """Test start_listening triggers advanced mode"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True

    audio_input_mock = MagicMock()
    audio_input_mock.enabled = True
    audio_input_mock.is_advanced.return_value = True
    audio_input_mock.speech_enabled = False
    mock_window.core.plugins.get.return_value = audio_input_mock

    plugin.start_listening()

    assert audio_input_mock.magic_word_detected is True
    audio_input_mock.toggle_speech.assert_called_once_with(True)


def test_start_listening_inactive(mock_window):
    """Test start_listening does nothing when inactive"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = False

    audio_input_mock = MagicMock()
    mock_window.core.plugins.get.return_value = audio_input_mock

    plugin.start_listening()

    audio_input_mock.toggle_recording_simple.assert_not_called()


def test_wake_word_activation_with_greeting(mock_window):
    """Test wake word activation speaks greeting"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True

    # Mock audio output
    audio_output_mock = MagicMock()
    audio_output_mock.enabled = True
    mock_window.core.plugins.get.return_value = audio_output_mock

    plugin.on_wake_word_activated()

    # Should dispatch AUDIO_READ_TEXT event
    mock_window.dispatch.assert_called()


def test_wake_word_activation_no_greeting(mock_window):
    """Test wake word activation without greeting"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = True
    plugin.options["greeting_enabled"]["value"] = False

    plugin.on_wake_word_activated()

    # Should NOT dispatch any event
    mock_window.dispatch.assert_not_called()


def test_wake_word_activation_inactive(mock_window):
    """Test wake word activation when plugin inactive"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.active = False

    plugin.on_wake_word_activated()

    mock_window.dispatch.assert_not_called()


def test_destroy(mock_window):
    """Test destroy cleans up state"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.active = True
    plugin.in_conversation = True

    plugin.destroy()

    assert plugin.active is False
    assert plugin.in_conversation is False


def test_default_values(mock_window):
    """Test default configuration values"""
    plugin = Plugin(window=mock_window)
    plugin.init_options()

    assert plugin.get_option_value("auto_listen_after_response") is True
    assert plugin.get_option_value("require_wake_word_each_turn") is False
    assert plugin.get_option_value("conversation_timeout") == 30
    assert plugin.get_option_value("greeting_enabled") is True
    assert plugin.get_option_value("greeting_text") == "Yes?"
    assert plugin.get_option_value("auto_enable_plugins") is True
    assert plugin.get_option_value("response_delay") == 0.5
