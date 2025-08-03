#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from llama_index.core.llms import ChatMessage, MessageRole
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.agents.memory import Memory

# Create a dummy history item
def make_item(agent_type, content, msg_id=None):
    extra = {}
    if agent_type == "input":
        extra["agent_input"] = True
    elif agent_type == "output":
        extra["agent_output"] = True
    return SimpleNamespace(
        extra=extra,
        final_input=content if agent_type == "input" else None,
        final_output=content if agent_type == "output" else None,
        msg_id=msg_id,
    )

# Fake window with required nested attributes
def create_fake_window(use_context, items):
    window = MagicMock()
    def config_get(key):
        if key == "max_total_tokens":
            return 100
        elif key == "use_context":
            return use_context
        return None
    window.core.config.get.side_effect = config_get
    window.core.tokens.from_user.return_value = 10
    window.core.models.get_num_ctx.return_value = 50
    window.core.ctx.get_history.return_value = items
    return window

@pytest.fixture
def fake_context():
    # Provide an object for context.ctx with an "input" attribute.
    fake_ctx = SimpleNamespace(input="test input")
    context = MagicMock(spec=BridgeContext)
    context.ctx = fake_ctx
    context.history = "history_data"
    context.mode = "test_mode"
    model = MagicMock()
    model.id = "model1"
    context.model = model
    return context

def test_prepare(fake_context):
    item1 = make_item("input", "user message")
    item2 = make_item("output", "assistant message", msg_id="resp1")
    window = create_fake_window(use_context=True, items=[item1, item2])
    memory = Memory(window)
    messages = memory.prepare(fake_context)
    assert len(messages) == 2
    assert messages[0].role == MessageRole.USER
    assert messages[0].content == "user message"
    assert messages[1].role == MessageRole.ASSISTANT
    assert messages[1].content == "assistant message"

def test_prepare_openai(fake_context):
    item1 = make_item("input", "user message")
    item2 = make_item("output", "assistant message", msg_id="resp1")
    window = create_fake_window(use_context=True, items=[item1, item2])
    memory = Memory(window)
    messages, prev_id = memory.prepare_openai(fake_context)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "user message"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "assistant message"
    assert prev_id == "resp1"

def test_no_context(fake_context):
    window = create_fake_window(use_context=False, items=[])
    memory = Memory(window)
    messages = memory.prepare(fake_context)
    messages_openai, prev_id = memory.prepare_openai(fake_context)
    assert messages == []
    assert messages_openai == []
    assert prev_id is None