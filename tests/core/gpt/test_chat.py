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
from pygpt_net.core.gpt.chat import Chat
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
    Test chat send
    """
    chat = Chat(mock_window)
    chat.window.core.config.get.side_effect = mock_get
    chat.window.core.models.get_num_ctx.return_value = 2048
    chat.window.core.ctx.get_prompt_items.return_value = []
    chat.window.core.ctx.get_model_ctx.return_value = 2048
    chat.window.core.tokens.from_messages.return_value = 10
    chat.build = MagicMock(return_value=[])

    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    chat.window.core.gpt.get_client = MagicMock(return_value=client)

    response = chat.send('test_prompt', 10)
    assert response.choices[0].message.content == 'test_response'


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
    chat.window.core.config.get.side_effect = mock_get
    chat.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    chat.window.core.ctx.get_prompt_items.return_value = items
    chat.window.core.ctx.get_model_ctx.return_value = 2048

    messages = chat.build('test_prompt', 'test_system_prompt')
    assert len(messages) == 4
    assert messages[0]['content'] == 'test_system_prompt'
    assert messages[1]['content'] == 'user message'
    assert messages[2]['content'] == 'AI message'
    assert messages[3]['content'] == 'test_prompt'
