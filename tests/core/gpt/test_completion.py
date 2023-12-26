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

import base64
import os

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.config import Config
from pygpt_net.core.gpt.completion import Completion
from pygpt_net.item.ctx import CtxItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.models = MagicMock()
    window.core.config = MagicMock(spec=Config)
    window.core.config.path = 'test_path'
    return window


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


def test_send(mock_window):
    """
    Test completion
    """
    completion = Completion(mock_window)
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


def test_reset_tokens(mock_window):
    """
    Test reset tokens
    """
    completion = Completion(mock_window)
    completion.input_tokens = 10
    completion.reset_tokens()
    assert completion.input_tokens == 0


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
    completion.count_used_tokens = MagicMock(return_value=4)
    completion.window.core.config.get.side_effect = mock_get
    completion.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    completion.window.core.ctx.get_prompt_items.return_value = items

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
    completion.window.core.config.get.side_effect = mock_get
    completion.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    completion.window.core.ctx.get_prompt_items.return_value = items

    message = completion.build('test_prompt', 'test_system_prompt', ai_name='AI', user_name='User')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'
