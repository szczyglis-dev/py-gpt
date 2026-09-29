#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 18:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.core.events import Event
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
    plugin.options["advanced"]["value"] = True
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
    plugin.ensure_provider_ready = MagicMock(return_value=True)
    plugin.options["advanced"]["value"] = True
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



def test_handle_toggle_on_provider_not_ready(mock_window):
    """Do not enable listening while a local provider is being prepared."""
    plugin = Plugin(window=mock_window)
    plugin.init_options()
    plugin.setup()
    plugin.handle_thread = MagicMock()
    plugin.ensure_provider_ready = MagicMock(return_value=False)
    plugin.options["advanced"]["value"] = True
    mock_window.ui.plugin_addon['audio.input'].btn_toggle = MagicMock()

    event = Event()
    event.name = "audio.input.toggle"
    event.data = {"value": True}
    event.ctx = CtxItem()
    plugin.handle(event)

    assert plugin.speech_enabled is False
    assert plugin.listening is False
    plugin.handle_thread.assert_not_called()
    mock_window.ui.plugin_addon['audio.input'].btn_toggle.setChecked.assert_called_once_with(False)


def test_ensure_provider_ready_non_local(mock_window):
    """Non-local providers do not require model preparation."""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    provider.id = "openai_whisper"
    plugin.get_provider = MagicMock(return_value=provider)

    assert plugin.ensure_provider_ready() is True
    provider.is_configured.assert_not_called()


def test_ensure_provider_ready_local_downloaded(mock_window):
    """A cached local Whisper model allows recording immediately."""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    provider.id = "openai_whisper_local"
    provider.is_configured.return_value = True
    provider.get_model_name.return_value = "base"
    provider.is_model_downloaded.return_value = True
    plugin.get_provider = MagicMock(return_value=provider)

    assert plugin.ensure_provider_ready() is True
    assert plugin.provider_preparing is False


def test_ensure_provider_ready_local_starts_prepare(mock_window):
    """A missing local Whisper checkpoint starts background preparation and blocks recording."""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    provider.id = "openai_whisper_local"
    provider.is_configured.return_value = True
    provider.get_model_name.return_value = "base"
    provider.is_model_downloaded.return_value = False
    plugin.get_provider = MagicMock(return_value=provider)
    plugin.set_status = MagicMock()

    with patch("pygpt_net.plugin.audio_input.worker.Worker") as worker_cls:
        worker = worker_cls.return_value
        result = plugin.ensure_provider_ready()

    assert result is False
    assert plugin.provider_preparing is True
    assert worker.prepare_model is True
    assert worker.prepare_provider is provider
    assert worker.prepare_model_name == "base"
    worker.signals.model_ready.connect.assert_called_once_with(plugin.handle_provider_ready)
    worker.signals.model_prepare_failed.connect.assert_called_once_with(plugin.handle_provider_prepare_failed)
    worker.run_async.assert_called_once()
    plugin.set_status.assert_called_once()
    mock_window.update_status.assert_called_once()


def test_ensure_provider_ready_local_already_preparing(mock_window):
    """Repeated toggle while downloading must not start a second model worker."""
    plugin = Plugin(window=mock_window)
    plugin.provider_preparing = True
    plugin.set_status = MagicMock()
    provider = MagicMock()
    provider.id = "openai_whisper_local"
    provider.is_configured.return_value = True
    provider.get_model_name.return_value = "small"
    plugin.get_provider = MagicMock(return_value=provider)

    with patch("pygpt_net.plugin.audio_input.worker.Worker") as worker_cls:
        result = plugin.ensure_provider_ready()

    assert result is False
    worker_cls.assert_not_called()
    plugin.set_status.assert_called_once()
    mock_window.update_status.assert_called_once()


def test_handle_provider_ready(mock_window):
    """Model-ready signal clears preparation state and publishes status."""
    plugin = Plugin(window=mock_window)
    plugin.provider_preparing = True
    plugin.set_status = MagicMock()

    plugin.handle_provider_ready("base")

    assert plugin.provider_preparing is False
    plugin.set_status.assert_called_once()
    mock_window.update_status.assert_called_once()


def test_handle_provider_prepare_failed(mock_window):
    """Preparation failure clears the guard so the user can retry."""
    plugin = Plugin(window=mock_window)
    plugin.provider_preparing = True
    plugin.set_status = MagicMock()

    plugin.handle_provider_prepare_failed("download failed")

    assert plugin.provider_preparing is False
    plugin.set_status.assert_called_once()
    mock_window.update_status.assert_called_once()


def test_handle_settings_changed_applies_whisper_memory_policy(mock_window):
    """Saving plugin settings applies Keep model in RAM / model-name changes immediately."""
    plugin = Plugin(window=mock_window)
    provider = MagicMock()
    plugin.get_providers = MagicMock(return_value={"openai_whisper_local": provider})

    event = Event()
    event.name = Event.PLUGIN_SETTINGS_CHANGED
    event.data = {}
    event.ctx = CtxItem()
    plugin.handle(event)

    provider.apply_memory_policy.assert_called_once()
