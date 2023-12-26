#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from langchain.schema import SystemMessage, HumanMessage, AIMessage
from pygpt_net.config import Config
from pygpt_net.core.chain.chat import Chat
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.config = MagicMock(spec=Config)
    window.core.config.path = 'test_path'
    window.core.models = MagicMock()
    return window


def test_build(mock_window):
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

    chat = Chat(mock_window)
    chat.window.core.config.get.return_value = True
    chat.window.core.ctx.get_all_items.return_value = items

    messages = chat.build('test_prompt', 'test_system_prompt')
    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert messages[0].content == 'test_system_prompt'
    assert messages[1].content == 'user message'
    assert messages[2].content == 'AI message'
    assert messages[3].content == 'test_prompt'


def test_send(mock_window):
    """
    Test chat
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window.core.models.get.return_value = model
    chat = Chat(mock_window)
    chat.build = MagicMock()
    chat.build.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chat.window.core.chain.llms = {'test': MagicMock()}
    chat.window.core.chain.llms['test'].chat = MagicMock(return_value=mock_chat_instance)
    response = chat.send('test_prompt')
    assert response == 'test_response'
    chat.build.assert_called_once_with('test_prompt', system_prompt=None, ai_name=None, user_name=None)
    chat.window.core.chain.llms['test'].chat.assert_called_once_with(
        mock_window.core.config.all(), model.langchain, False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')
