#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #
import os
import base64
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pygpt_net.controller.chat.audio import Audio
from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.core.bridge.context import MultimodalContext, BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem

@pytest.fixture
def dummy_window(tmp_path):
    window = MagicMock()
    config = MagicMock()
    config.get.return_value = None
    config.get_user_path.return_value = str(tmp_path)
    window.core = MagicMock()
    window.core.config = config
    audio_ctrl = MagicMock()
    window.controller = MagicMock()
    window.controller.audio = audio_ctrl
    node_input = MagicMock()
    node_input.toPlainText.return_value = "Test prompt"
    ui = MagicMock()
    ui.nodes = {"input": node_input}
    window.ui = ui
    window.dispatch = MagicMock()
    return window

@pytest.fixture
def audio_obj(dummy_window):
    return Audio(window=dummy_window)

def test_init(dummy_window):
    obj = Audio(window=dummy_window)
    assert obj.window is dummy_window
    assert obj.audio_file == "chat_output.wav"
    assert obj.tmp_input is False
    assert obj.tmp_output is False

def test_setup(audio_obj):
    audio_obj.setup()

def test_enabled_false(audio_obj, dummy_window):
    dummy_window.core.config.get.return_value = "text"
    assert audio_obj.enabled() is False

def test_enabled_true(audio_obj, dummy_window):
    dummy_window.core.config.get.return_value = MODE_AUDIO
    assert audio_obj.enabled() is True

def test_update_enable(audio_obj, dummy_window):
    dummy_window.core.config.get.return_value = MODE_AUDIO
    dummy_window.controller.audio.is_output_enabled.return_value = False
    dummy_window.controller.audio.is_input_enabled.return_value = False
    audio_obj.update()
    dummy_window.controller.audio.enable_input.assert_called_once()
    assert audio_obj.tmp_input is True

def test_update_no_enable(audio_obj, dummy_window):
    dummy_window.core.config.get.return_value = MODE_AUDIO
    dummy_window.controller.audio.is_output_enabled.return_value = True
    dummy_window.controller.audio.is_input_enabled.return_value = True
    audio_obj.update()
    dummy_window.controller.audio.enable_output.assert_not_called()
    dummy_window.controller.audio.enable_input.assert_not_called()
    assert audio_obj.tmp_output is False
    assert audio_obj.tmp_input is False

def test_update_disable(audio_obj, dummy_window):
    dummy_window.core.config.get.return_value = "text"
    audio_obj.tmp_output = True
    audio_obj.tmp_input = True
    audio_obj.update()
    dummy_window.controller.audio.disable_input.assert_called_once()

def test_handle_output(monkeypatch, audio_obj, dummy_window):
    data = b"test audio"
    encoded = base64.b64encode(data).decode()
    ctx = MagicMock(spec=CtxItem)
    ctx.is_audio = True
    ctx.audio_output = encoded
    ctx.audio_read_allowed.return_value = True
    m = mock_open()
    monkeypatch.setattr("builtins.open", m)
    audio_obj.handle_output(ctx)
    user_path = dummy_window.core.config.get_user_path.return_value
    wav_path = os.path.join(user_path, audio_obj.audio_file)
    m.assert_called_once_with(wav_path, "wb")
    handle = m()
    handle.write.assert_called_once_with(data)
    dummy_window.controller.audio.play_chat_audio.assert_called_once_with(wav_path)

def test_handle_output_no_action(monkeypatch, audio_obj, dummy_window):
    ctx = MagicMock(spec=CtxItem)
    ctx.is_audio = False
    ctx.audio_output = None
    ctx.audio_read_allowed.return_value = True
    m = mock_open()
    monkeypatch.setattr("builtins.open", m)
    audio_obj.handle_output(ctx)
    dummy_window.controller.audio.play_chat_audio.assert_not_called()

def test_handle_output_read_not_allowed(monkeypatch, audio_obj, dummy_window):
    data = b"test audio"
    encoded = base64.b64encode(data).decode()
    ctx = MagicMock(spec=CtxItem)
    ctx.is_audio = True
    ctx.audio_output = encoded
    ctx.audio_read_allowed.return_value = False
    m = mock_open()
    monkeypatch.setattr("builtins.open", m)
    audio_obj.handle_output(ctx)
    dummy_window.controller.audio.play_chat_audio.assert_not_called()

def test_handle_input(tmp_path, audio_obj, dummy_window):
    file_path = tmp_path / "input.wav"
    file_path.write_bytes(b"input data")
    with patch("pygpt_net.controller.chat.audio.KernelEvent") as mock_kernel_event:
        fake_event = MagicMock()
        mock_kernel_event.return_value = fake_event
        audio_obj.handle_input(str(file_path))
        mock_kernel_event.assert_called_once()
        args, _ = mock_kernel_event.call_args
        payload = args[1]
        assert "context" in payload
        bridge_ctx = payload["context"]
        assert bridge_ctx.prompt == dummy_window.ui.nodes["input"].toPlainText()
        assert isinstance(bridge_ctx.multimodal_ctx, MultimodalContext)
        assert bridge_ctx.multimodal_ctx.audio_data == b"input data"
        assert bridge_ctx.multimodal_ctx.is_audio_input is True
        dummy_window.dispatch.assert_called_once_with(fake_event)