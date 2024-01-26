#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.26 18:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window_conf
from pygpt_net.core.chain.completion import Completion
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def test_build(mock_window_conf):
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

    mock_window_conf.core.models.get_num_ctx = MagicMock(return_value=100)
    completion = Completion(mock_window_conf)
    completion.window.core.config.get.return_value = True
    completion.window.core.ctx.get_prompt_items.return_value = items

    model = ModelItem()
    message = completion.build(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        model=model,
    )
    assert message == 'test_system_prompt\nuser message\nAI message\ntest_prompt'


def test_build_with_names(mock_window_conf):
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

    completion = Completion(mock_window_conf)
    completion.window.core.config.get.return_value = True
    mock_window_conf.core.models.get_num_ctx = MagicMock(return_value=100)
    completion.window.core.ctx.get_prompt_items.return_value = items

    model = ModelItem()

    message = completion.build(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        ai_name='AI',
        user_name='User',
        model=model,
    )
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'


def test_send(mock_window_conf):
    """
    Test completion
    """
    model = ModelItem()
    model.name = 'test'
    model.langchain = {'provider': 'test'}

    mock_window_conf.core.models.get.return_value = model
    completion = Completion(mock_window_conf)
    completion.build = MagicMock()
    completion.build.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    completion.window.core.llm.llms = {'test': MagicMock()}
    completion.window.core.llm.llms['test'].completion = MagicMock(return_value=mock_chat_instance)
    response = completion.send(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        ai_name='AI',
        user_name='User',
        model=model,
    )
    assert response == 'test_response'
    completion.build.assert_called_once_with(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        ai_name='AI',
        user_name='User',
        model=model,
    )
    completion.window.core.llm.llms['test'].completion.assert_called_once_with(
        mock_window_conf,
        model,
        False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')

