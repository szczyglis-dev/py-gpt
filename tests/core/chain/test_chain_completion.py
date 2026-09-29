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

from tests.mocks import mock_window_conf
from pygpt_net.core.chain.completion import Completion
from pygpt_net.core.types import MODE_COMPLETION
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def _configure_build_window(window, history):
    window.core.tokens = MagicMock()
    window.core.tokens.from_user.return_value = 9
    window.core.tokens.from_text.return_value = 31
    window.core.ctx = MagicMock()
    window.core.ctx.get_history.return_value = history

    def config_get(key, default=None):
        return {
            "max_total_tokens": 100,
            "use_context": True,
        }.get(key, default)

    window.core.config.get.side_effect = config_get


def test_build(mock_window_conf):
    """Build an unnamed completion prompt from system text and history."""
    first = CtxItem()
    first.input = "user message"
    second = CtxItem()
    second.output = "AI message"
    history = [first, second]
    _configure_build_window(mock_window_conf, history)

    completion = Completion(mock_window_conf)
    model = ModelItem("test-model")
    model.ctx = 80

    message = completion.build(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
    )

    assert message == "test_system_prompt\nuser message\nAI message\ntest_prompt"
    mock_window_conf.core.ctx.get_history.assert_called_once_with(
        None,
        "test-model",
        "langchain",
        9,
        80,
    )
    mock_window_conf.core.tokens.from_text.assert_called_once_with(
        message,
        "test-model",
    )
    assert completion.get_used_tokens() == 31


def test_build_with_names(mock_window_conf):
    """Build a completion prompt with explicit user and assistant labels."""
    first = CtxItem()
    first.input = "user message"
    first.input_name = "User"
    first.output_name = "AI"

    second = CtxItem()
    second.output = "AI message"
    second.input_name = "User"
    second.output_name = "AI"

    history = [first, second]
    _configure_build_window(mock_window_conf, history)

    completion = Completion(mock_window_conf)
    model = ModelItem("test-model")
    model.ctx = 80

    message = completion.build(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        ai_name="AI",
        user_name="User",
        model=model,
    )

    assert message == (
        "test_system_prompt\n"
        "User: user message\n"
        "AI: AI message\n"
        "User: test_prompt\n"
        "AI:"
    )


def test_send(mock_window_conf):
    """Send initializes the completion provider and invokes the built prompt."""
    model = ModelItem("test-model")
    model.langchain = {"provider": "test"}

    provider = MagicMock()
    llm = MagicMock()
    llm.invoke.return_value = "test_response"
    provider.completion.return_value = llm
    mock_window_conf.core.llm = MagicMock()
    mock_window_conf.core.llm.llms = {"test": provider}

    completion = Completion(mock_window_conf)
    completion.build = MagicMock(return_value="test_messages")

    response = completion.send(
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
        MODE_COMPLETION,
    )
    provider.completion.assert_called_once_with(mock_window_conf, model, False)
    completion.build.assert_called_once_with(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
        ai_name="AI",
        user_name="User",
    )
    llm.invoke.assert_called_once_with("test_messages")
