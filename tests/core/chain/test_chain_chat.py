#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from langchain.schema import SystemMessage, HumanMessage, AIMessage

from tests.mocks import mock_window_conf
from pygpt_net.core.chain.chat import Chat
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def test_build(mock_window_conf):
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

    chat = Chat(mock_window_conf)
    chat.window.core.config.get.return_value = True
    mock_window_conf.core.models.get_num_ctx = MagicMock(return_value=100)
    chat.window.core.ctx.get_history.return_value = items

    model = ModelItem()
    messages = chat.build(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        model=model,
    )
    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert messages[0].content == 'test_system_prompt'
    assert messages[1].content == 'user message'
    assert messages[2].content == 'AI message'
    assert messages[3].content == 'test_prompt'


def test_send(mock_window_conf):
    """
    Test chat
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window_conf.core.models.get.return_value = model
    chat = Chat(mock_window_conf)
    chat.build = MagicMock()
    chat.build.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chat.window.core.llm.llms = {'test': MagicMock()}
    chat.window.core.llm.llms['test'].chat = MagicMock(return_value=mock_chat_instance)
    response = chat.send(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        ai_name='AI',
        user_name='User',
        model=model,
    )
    assert response == 'test_response'
    chat.build.assert_called_once_with(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        model=model,
        history=None,
        ai_name='AI',
        user_name='User',
    )
    chat.window.core.llm.llms['test'].chat.assert_called_once_with(
        mock_window_conf, model, False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')
