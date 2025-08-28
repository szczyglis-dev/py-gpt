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

import pytest
from unittest.mock import MagicMock
import types
from pygpt_net.provider.api.openai.completion import Completion

@pytest.fixture
def dummy_window():
    window = MagicMock()
    core = MagicMock()
    tokens = MagicMock()
    tokens.from_user.return_value = 10
    tokens.from_text.return_value = 20
    config = MagicMock()
    config.get.side_effect = lambda key: {
        'temperature': 0.7,
        'top_p': 1,
        'frequency_penalty': 0,
        'presence_penalty': 0,
        'max_total_tokens': 1000,
        'use_context': True
    }[key]
    gpt = MagicMock()
    client = MagicMock()
    client.completions.create.return_value = {"result": "response"}
    gpt.get_client.return_value = client
    core.tokens = tokens
    core.config = config
    core.api.openai = gpt
    core.ctx.get_history.return_value = []
    window.core = core
    return window

@pytest.fixture
def dummy_model():
    model = MagicMock()
    model.id = "model-1"
    model.ctx = 100
    return model

@pytest.fixture
def dummy_context(dummy_model):
    context = MagicMock()
    context.prompt = "Test prompt"
    context.stream = False
    context.max_tokens = 50
    context.system_prompt = "System prompt"
    context.model = dummy_model
    ctx_item = MagicMock()
    ctx_item.input_name = "User"
    ctx_item.output_name = "AI"
    context.ctx = ctx_item
    context.history = []
    return context

def test_init(dummy_window):
    comp = Completion(window=dummy_window)
    assert comp.window == dummy_window
    assert comp.input_tokens == 0

def test_reset_tokens(dummy_window):
    comp = Completion(window=dummy_window)
    comp.input_tokens = 50
    comp.reset_tokens()
    assert comp.input_tokens == 0

def test_get_used_tokens(dummy_window):
    comp = Completion(window=dummy_window)
    comp.input_tokens = 42
    assert comp.get_used_tokens() == 42

def test_build_with_context(dummy_window, dummy_model):
    item1 = types.SimpleNamespace(input_name="User", output_name="AI", final_input="Hello", final_output="Hi")
    item2 = types.SimpleNamespace(input_name="", output_name="", final_input="Second prompt", final_output="Second answer")
    dummy_window.core.ctx.get_history.return_value = [item1, item2]
    comp = Completion(window=dummy_window)
    message = comp.build("Test prompt", "System prompt", dummy_model, history=[], ai_name="GPT", user_name="User")
    expected = "System prompt\nUser: Hello\nAI: Hi\nSecond prompt\nSecond answer\nUser: Test prompt\nGPT:"
    assert message == expected
    assert comp.input_tokens == 20

def test_build_without_context(dummy_window, dummy_model):
    dummy_window.core.config.get.side_effect = lambda key: {
        'temperature': 0.7,
        'top_p': 1,
        'frequency_penalty': 0,
        'presence_penalty': 0,
        'max_total_tokens': 1000,
        'use_context': False
    }[key]
    comp = Completion(window=dummy_window)
    message = comp.build("Test prompt", "System prompt", dummy_model, history=[], ai_name="GPT", user_name="User")
    expected = "System prompt\nUser: Test prompt\nGPT:"
    assert message == expected
    assert comp.input_tokens == 20

def test_send(dummy_window, dummy_context):
    comp = Completion(window=dummy_window)
    comp.build = MagicMock(return_value="constructed prompt")
    response = comp.send(dummy_context)
    client = dummy_window.core.api.openai.get_client.return_value
    args, kwargs = client.completions.create.call_args
    assert kwargs["prompt"] == "constructed prompt"
    assert kwargs["model"] == dummy_context.model.id
    assert kwargs["temperature"] == 0.7
    assert kwargs["top_p"] == 1
    assert kwargs["frequency_penalty"] == 0
    assert kwargs["presence_penalty"] == 0
    assert kwargs["stop"] == ["User:"]
    assert kwargs["stream"] == dummy_context.stream
    assert kwargs["max_tokens"] == 50
    assert response == {"result": "response"}

def test_send_with_text_davinci(dummy_window, dummy_context):
    dummy_context.model.id = "text-davinci-002"
    comp = Completion(window=dummy_window)
    comp.build = MagicMock(return_value="constructed prompt")
    response = comp.send(dummy_context)
    client = dummy_window.core.api.openai.get_client.return_value
    args, kwargs = client.completions.create.call_args
    assert kwargs["model"] == "gpt-3.5-turbo-instruct"
    assert response == {"result": "response"}

def test_send_with_ctx_none(monkeypatch, dummy_window, dummy_context):
    dummy_context.ctx = None
    dummy_ctx = MagicMock()
    dummy_ctx.input_name = ""
    dummy_ctx.output_name = ""
    comp = Completion(window=dummy_window)
    comp.build = MagicMock(return_value="constructed prompt")
    response = comp.send(dummy_context)
    client = dummy_window.core.api.openai.get_client.return_value
    args, kwargs = client.completions.create.call_args
    assert kwargs["stop"] == ""
    assert response == {"result": "response"}