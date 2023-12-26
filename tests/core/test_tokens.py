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

from pygpt_net.config import Config
from pygpt_net.core.ctx import Ctx
from pygpt_net.core.tokens import *
from pygpt_net.item.ctx import CtxItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.core = MagicMock()
    window.core.config = MagicMock(spec=Config)
    window.core.config.path = 'test_path'
    return window


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200


def test_num_tokens_from_string():
    """
    Test num_tokens_from_string
    """
    text = "This is a test"
    num_tokens_from_string = MagicMock(return_value=4)
    assert num_tokens_from_string(text, 'gpt-3.5') == 4


def test_num_tokens_extra():
    """
    Test num_tokens_extra
    """
    model = "gpt-4-0613"
    assert num_tokens_extra() == 3


def test_num_tokens_prompt():
    """
    Test num_tokens_prompt
    """
    text = "This is a test"
    input_name = "test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_prompt(text, input_name, model) == 12


def test_num_tokens_completion():
    """
    Test num_tokens_completion
    """
    text = "This is a test"
    model = "gpt-3.5-turbo-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_completion(text, model) == 8


def test_num_tokens_only():
    """
    Test num_tokens_only
    """
    text = "This is a test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_only(text, model) == 8

def test_num_tokens_from_messages():
    """
    Test num_tokens_from_messages
    """
    messages = [
        {
            'name': 'test',
            'content': 'This is a test'
        },
        {
            'name': 'test',
            'content': 'This is a second test'
        }
    ]
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_from_messages(messages, model) == 43


def test_num_tokens_from_context_item():
    """
    Test num_tokens_from_context_item
    """
    item = CtxItem()
    item.input = "This is a test"
    item.output = "This is a second test"
    item.input_name = "test"
    item.output_name = "test"
    item.input_tokens = 4
    item.output_tokens = 4
    item.total_tokens = 8
    item.input_timestamp = 1
    item.output_timestamp = 2

    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_from_context_item(item, 'chat', model) == 56


def test_get_tokens_values():
    """
    Test get_tokens_values
    """
    model = "gpt-4-0613"
    assert get_tokens_values(model) == ('gpt-4-0613', 3, 1)
