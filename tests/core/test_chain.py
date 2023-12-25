#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 02:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from langchain.schema import SystemMessage, HumanMessage, AIMessage
from pygpt_net.core.item.ctx import CtxItem
from pygpt_net.core.item.model import ModelItem

from pygpt_net.core.config import Config
from pygpt_net.core.chain import Chain


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.app = MagicMock()
    window.app.config = MagicMock(spec=Config)
    window.app.config.path = 'test_path'
    window.app.models = MagicMock()
    return window


def test_build_chat_messages(mock_window):
    """
    Test build chat messages
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.window.app.config.get.return_value = True
    chain.window.app.ctx.get_all_items.return_value = items

    messages = chain.build_chat_messages('test_prompt')
    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert messages[0].content == 'test_system_prompt'
    assert messages[1].content == 'user message'
    assert messages[2].content == 'AI message'
    assert messages[3].content == 'test_prompt'


def test_build_completion(mock_window):
    """
    Test build completion
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.window.app.config.get.return_value = True
    chain.window.app.ctx.get_all_items.return_value = items

    message = chain.build_completion('test_prompt')
    assert message == 'test_system_prompt\nuser message\nAI message\ntest_prompt'


def test_build_completion_with_names(mock_window):
    """
    Test build completion with names
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.user_name = 'User'
    chain.ai_name = 'AI'
    chain.window.app.config.get.return_value = True
    chain.window.app.ctx.get_all_items.return_value = items

    message = chain.build_completion('test_prompt')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'


def test_chat(mock_window):
    """
    Test chat
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window.app.models.get.return_value = model
    chain = Chain(mock_window)
    chain.build_chat_messages = MagicMock()
    chain.build_chat_messages.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chain.llms = {'test': MagicMock()}
    chain.llms['test'].chat = MagicMock(return_value=mock_chat_instance)
    response = chain.chat('test_prompt')
    assert response == 'test_response'
    chain.build_chat_messages.assert_called_once_with('test_prompt')
    chain.llms['test'].chat.assert_called_once_with(
        mock_window.app.config.all(), model.langchain, False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')


def test_completion(mock_window):
    """
    Test completion
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window.app.models.get.return_value = model
    chain = Chain(mock_window)
    chain.build_completion = MagicMock()
    chain.build_completion.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chain.llms = {'test': MagicMock()}
    chain.llms['test'].completion = MagicMock(return_value=mock_chat_instance)
    response = chain.completion('test_prompt')
    assert response == 'test_response'
    chain.build_completion.assert_called_once_with('test_prompt')
    chain.llms['test'].completion.assert_called_once_with(
        mock_window.app.config.all(), model.langchain, False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')


def test_call(mock_window):
    """
    Test call
    """
    ctx = CtxItem()
    ctx.input = 'test_input'

    model = ModelItem()
    model.name = 'test'
    model.langchain = {
        'provider': 'test',
        'mode': ['chat', 'completion']
    }

    mock_window.app.models.get.return_value = model
    chain = Chain(mock_window)
    chain.chat = MagicMock()
    chain.chat.content = MagicMock()
    chain.completion = MagicMock()
    chain.chat.content.return_value = 'test_chat_response'
    chain.completion.return_value = 'test_completion_response'

    chain.call('test_text', ctx)
    chain.chat.assert_called_once_with('test_text', False)
