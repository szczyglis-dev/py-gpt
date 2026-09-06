#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.07 00:30:00                  #
# ================================================== #

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from tests.mocks import mock_window_conf
from pygpt_net.core.chain.chat import Chat
from pygpt_net.core.types import MODE_CHAT
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def _configure_build_window(window, history):
    window.core.tokens = MagicMock()
    window.core.tokens.from_user.return_value = 7
    window.core.tokens.from_langchain_messages.return_value = 23
    window.core.ctx = MagicMock()
    window.core.ctx.get_history.return_value = history

    def config_get(key, default=None):
        return {
            "max_total_tokens": 100,
            "use_context": True,
        }.get(key, default)

    window.core.config.get.side_effect = config_get


def test_build(mock_window_conf):
    """Build chat messages from system prompt, history and current prompt."""
    first = CtxItem()
    first.input = "user message"
    second = CtxItem()
    second.output = "AI message"
    history = [first, second]
    _configure_build_window(mock_window_conf, history)

    chat = Chat(mock_window_conf)
    model = ModelItem("test-model")
    model.ctx = 80

    messages = chat.build(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
    )

    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert isinstance(messages[3], HumanMessage)
    assert [message.content for message in messages] == [
        "test_system_prompt",
        "user message",
        "AI message",
        "test_prompt",
    ]
    mock_window_conf.core.ctx.get_history.assert_called_once_with(
        None,
        "test-model",
        "langchain",
        7,
        80,
    )
    mock_window_conf.core.tokens.from_langchain_messages.assert_called_once_with(
        messages,
        "test-model",
    )
    assert chat.get_used_tokens() == 23


def test_send(mock_window_conf):
    """Send initializes the selected provider and invokes the built chat payload."""
    model = ModelItem("test-model")
    model.langchain = {"provider": "test"}

    provider = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = "test_response"
    provider.chat.return_value = llm
    mock_window_conf.core.llm = MagicMock()
    mock_window_conf.core.llm.llms = {"test": provider}

    chat = Chat(mock_window_conf)
    chat.build = MagicMock(return_value="test_messages")

    response = chat.send(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        ai_name="AI",
        user_name="User",
        model=model,
    )

    assert response == "test_response"
    provider.init.assert_called_once_with(
        mock_window_conf,
        model,
        "langchain",
        MODE_CHAT,
    )
    provider.chat.assert_called_once_with(mock_window_conf, model, False)
    chat.build.assert_called_once_with(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
        history=None,
        ai_name="AI",
        user_name="User",
    )
    llm.invoke.assert_called_once_with("test_messages")
