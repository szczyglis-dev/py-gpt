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
from pygpt_net.core.chain.completion import Completion
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
    Test build completion
    """
    items = []
    ctx_item = CtxItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = CtxItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    completion = Completion(mock_window)
    completion.window.core.config.get.return_value = True
    completion.window.core.ctx.get_all_items.return_value = items

    message = completion.build('test_prompt', 'test_system_prompt')
    assert message == 'test_system_prompt\nuser message\nAI message\ntest_prompt'


def test_build_with_names(mock_window):
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

    completion = Completion(mock_window)
    completion.window.core.config.get.return_value = True
    completion.window.core.ctx.get_all_items.return_value = items

    message = completion.build('test_prompt', 'test_system_prompt', ai_name='AI', user_name='User')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'


def test_send(mock_window):
    """
    Test completion
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window.core.models.get.return_value = model
    completion = Completion(mock_window)
    completion.build = MagicMock()
    completion.build.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    completion.window.core.chain.llms = {'test': MagicMock()}
    completion.window.core.chain.llms['test'].completion = MagicMock(return_value=mock_chat_instance)
    response = completion.send('test_prompt')
    assert response == 'test_response'
    completion.build.assert_called_once_with('test_prompt', system_prompt=None, ai_name=None, user_name=None)
    completion.window.core.chain.llms['test'].completion.assert_called_once_with(
        mock_window.core.config.all(), model.langchain, False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')

