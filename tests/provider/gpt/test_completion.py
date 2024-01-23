#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window_conf
from pygpt_net.provider.gpt.completion import Completion
from pygpt_net.item.ctx import CtxItem


def mock_get(key):
    if key == "use_context":
        return True
    elif key == "model":
        return "gpt-3.5-turbo"
    elif key == "mode":
        return "chat"
    elif key == "max_total_tokens":
        return 2048
    elif key == "context_threshold":
        return 200


def test_send(mock_window_conf):
    """
    Test completion
    """
    completion = Completion(mock_window_conf)
    completion.window.core.config.get.side_effect = mock_get
    completion.window.core.models.get_num_ctx.return_value = 2048
    completion.window.core.ctx.get_prompt_items.return_value = []
    completion.window.core.ctx.get_model_ctx.return_value = 2048
    completion.build = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = 'test_response'
    client.completions.create.return_value = mock_response
    completion.window.core.gpt.get_client = MagicMock(return_value=client)

    completion.window.core.ctx.add_item = MagicMock()
    response = completion.send('test_prompt', 10)
    assert response.choices[0].text == 'test_response'


def test_reset_tokens(mock_window_conf):
    """
    Test reset tokens
    """
    completion = Completion(mock_window_conf)
    completion.input_tokens = 10
    completion.reset_tokens()
    assert completion.input_tokens == 0


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

    completion = Completion(mock_window_conf)
    completion.count_used_tokens = MagicMock(return_value=4)
    completion.window.core.config.get.side_effect = mock_get
    completion.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    completion.window.core.ctx.get_prompt_items.return_value = items

    message = completion.build('test_prompt', 'test_system_prompt')
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
    completion.window.core.config.get.side_effect = mock_get
    completion.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    completion.window.core.ctx.get_prompt_items.return_value = items

    message = completion.build('test_prompt', 'test_system_prompt', ai_name='AI', user_name='User')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'
