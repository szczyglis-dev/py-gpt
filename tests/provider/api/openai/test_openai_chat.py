#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import time
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from pygpt_net.provider.api.openai.chat import Chat
from pygpt_net.item.ctx import CtxItem

@pytest.fixture
def dummy_window():
    window = MagicMock()
    window.core = MagicMock()
    window.core.api.openai = MagicMock()
    window.core.api.openai.get_client = MagicMock()
    window.core.api.openai.tools = MagicMock()
    window.core.api.openai.tools.prepare = MagicMock(return_value=[])
    window.core.tokens = MagicMock()
    window.core.tokens.from_messages = MagicMock(return_value=10)
    window.core.tokens.from_user = MagicMock(return_value=5)
    config_values = {
        'presence_penalty': 0.1,
        'frequency_penalty': 0.2,
        'temperature': 0.3,
        'top_p': 0.9,
        'max_total_tokens': 4096,
        'use_context': False,
        'func_call.native': False
    }
    window.core.config = MagicMock()
    window.core.config.get = MagicMock(side_effect=lambda k, default=None: config_values.get(k, default))
    window.core.ctx = MagicMock()
    window.core.ctx.get_history = MagicMock(return_value=[])
    window.core.api.openai.vision = MagicMock()
    window.core.api.openai.vision.build_content = MagicMock(side_effect=lambda content, attachments: content + " vision")
    window.core.api.openai.audio = MagicMock()
    window.core.api.openai.audio.build_content = MagicMock(side_effect=lambda content, multimodal_ctx: content + " audio")
    window.core.command = MagicMock()
    window.core.command.unpack_tool_calls = MagicMock(return_value=["unpacked_tool"])
    window.core.plugins = MagicMock()
    window.core.plugins.get_option = MagicMock(return_value="test_voice")
    return window

@pytest.fixture
def dummy_model():
    model = MagicMock()
    model.id = "gpt-3-chat"
    model.ctx = 4096
    model.extra = {}
    model.mode = ["chat"]
    model.is_gpt = MagicMock(return_value=True)
    model.is_image_input = MagicMock(return_value=False)
    model.is_audio_input = MagicMock(return_value=False)
    return model

@pytest.fixture
def dummy_ctx():
    ctx = CtxItem()
    ctx.input_name = "user"
    ctx.output_name = "assistant"
    return ctx

@pytest.fixture
def dummy_context(dummy_model, dummy_ctx):
    context = SimpleNamespace()
    context.prompt = "Hello"
    context.stream = True
    context.max_tokens = 100
    context.system_prompt = "system"
    context.mode = "chat"
    context.model = dummy_model
    context.external_functions = []
    context.attachments = {}
    context.multimodal_ctx = None
    context.history = []
    context.ctx = dummy_ctx
    return context

def test_reset_tokens(dummy_window):
    chat = Chat(window=dummy_window)
    chat.input_tokens = 5
    chat.reset_tokens()
    assert chat.input_tokens == 0

def test_get_used_tokens(dummy_window):
    chat = Chat(window=dummy_window)
    chat.input_tokens = 7
    assert chat.get_used_tokens() == 7

def test_build_without_history(dummy_window, dummy_model, dummy_ctx):
    chat = Chat(window=dummy_window)
    messages = chat.build("Hello", "system", dummy_model, history=[], attachments=None, ai_name="assistant", user_name="user", multimodal_ctx=None)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "system"
    assert messages[1]["role"] == "user"
    assert "Hello" in messages[1]["content"]
    assert chat.input_tokens == 10

def test_build_with_vision(dummy_window, dummy_model, dummy_ctx):
    dummy_model.is_image_input = MagicMock(return_value=True)
    chat = Chat(window=dummy_window)
    messages = chat.build("Hello", "system", dummy_model, history=[], attachments={"file": "dummy"}, ai_name="assistant", user_name="user", multimodal_ctx=None)
    assert messages[-1]["content"] == "Hello vision"

def test_build_with_audio(dummy_window, dummy_model, dummy_ctx):
    dummy_model.is_audio_input = MagicMock(return_value=True)
    chat = Chat(window=dummy_window)
    messages = chat.build("Hello", "system", dummy_model, history=[], attachments=None, ai_name="assistant", user_name="user", multimodal_ctx="audio_ctx")
    assert messages[-1]["content"] == "Hello audio"

def test_send_chat_mode(dummy_window, dummy_context):
    chat = Chat(window=dummy_window)
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = MagicMock(return_value="response")
    dummy_window.core.api.openai.get_client.return_value = client
    response = chat.send(dummy_context)
    assert response == "response"
    args, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == dummy_context.model.id
    assert kwargs["stream"] == dummy_context.stream

def test_unpack_response_completion(dummy_window, dummy_ctx):
    chat = Chat(window=dummy_window)
    response = SimpleNamespace(choices=[SimpleNamespace(text=" output text ")], usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2))
    chat.unpack_response("completion", response, dummy_ctx)
    assert dummy_ctx.output == "output text"
    assert dummy_ctx.input_tokens == 1
    assert dummy_ctx.output_tokens == 2
    assert dummy_ctx.total_tokens == 3

def test_unpack_response_chat_no_tool(dummy_window, dummy_ctx):
    msg = SimpleNamespace(content=" chat output ", tool_calls=None)
    choice = SimpleNamespace(message=msg)
    response = SimpleNamespace(choices=[choice], usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4))
    chat = Chat(window=dummy_window)
    chat.unpack_response("chat", response, dummy_ctx)
    assert dummy_ctx.output == "chat output"
    assert dummy_ctx.input_tokens == 3
    assert dummy_ctx.output_tokens == 4
    assert dummy_ctx.total_tokens == 7

def test_unpack_response_chat_with_tool(dummy_window, dummy_ctx):
    msg = SimpleNamespace(content=" chat output ", tool_calls=[{"dummy": "call"}])
    choice = SimpleNamespace(message=msg)
    response = SimpleNamespace(choices=[choice], usage=SimpleNamespace(prompt_tokens=5, completion_tokens=6))
    chat = Chat(window=dummy_window)
    chat.unpack_response("chat", response, dummy_ctx)
    assert dummy_ctx.output == "chat output"
    assert dummy_ctx.tool_calls == ["unpacked_tool"]
    assert dummy_ctx.input_tokens == 5
    assert dummy_ctx.output_tokens == 6
    assert dummy_ctx.total_tokens == 11

def test_unpack_response_audio_with_audio(dummy_window, dummy_ctx):
    audio = SimpleNamespace(data="audio_data", id="audio123", expires_at=999999, transcript=" audio transcript ")
    msg = SimpleNamespace(audio=audio, content=None, tool_calls=None)
    choice = SimpleNamespace(message=msg)
    response = SimpleNamespace(choices=[choice], usage=SimpleNamespace(prompt_tokens=7, completion_tokens=8))
    chat = Chat(window=dummy_window)
    chat.audio_prev_id = None
    chat.audio_prev_expires_ts = None
    chat.unpack_response("audio", response, dummy_ctx)
    assert dummy_ctx.output == " audio transcript "
    assert dummy_ctx.audio_output == "audio_data"
    assert dummy_ctx.audio_id == "audio123"
    assert dummy_ctx.audio_expires_ts == 999999
    assert dummy_ctx.is_audio is True
    assert chat.audio_prev_id == "audio123"
    assert chat.audio_prev_expires_ts == 999999
    assert dummy_ctx.input_tokens == 7
    assert dummy_ctx.output_tokens == 8
    assert dummy_ctx.total_tokens == 15

def test_unpack_response_audio_without_audio(dummy_window, dummy_ctx):
    msg = SimpleNamespace(audio=None, content=" fallback audio content ", tool_calls=None)
    choice = SimpleNamespace(message=msg)
    response = SimpleNamespace(choices=[choice], usage=SimpleNamespace(prompt_tokens=9, completion_tokens=10))
    chat = Chat(window=dummy_window)
    chat.audio_prev_id = "prev_audio"
    chat.audio_prev_expires_ts = 888888
    chat.unpack_response("audio", response, dummy_ctx)
    assert dummy_ctx.output == " fallback audio content "
    assert dummy_ctx.audio_id == "prev_audio"
    assert dummy_ctx.audio_expires_ts == 888888
    assert dummy_ctx.input_tokens == 9
    assert dummy_ctx.output_tokens == 10
    assert dummy_ctx.total_tokens == 19