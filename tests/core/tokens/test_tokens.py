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

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window_conf
from pygpt_net.core.tokens import Tokens
from pygpt_net.item.ctx import CtxItem


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200


def test_from_str():
    """Test from_str"""
    text = "This is a test"
    Tokens.from_str = MagicMock(return_value=4)
    assert Tokens.from_str(text, 'gpt-3.5') == 4


def test_get_extra():
    """Test get_extra"""
    model = "gpt-4-0613"
    assert Tokens.get_extra() == 3


def test_from_prompt():
    """Test from_prompt"""
    text = "This is a test"
    input_name = "test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.tokens.Tokens.from_str', return_value=8):
        assert Tokens.from_prompt(text, input_name, model) == 12


def test_from_text():
    """Test from_text"""
    text = "This is a test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.tokens.Tokens.from_str', return_value=8):
        assert Tokens.from_text(text, model) == 8


def test_from_messages():
    """Test from_messages"""
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
    with patch('pygpt_net.core.tokens.tokens.Tokens.from_str', return_value=8):
        assert Tokens.from_messages(messages, model) == 43


def test_from_ctx():
    """Test from_ctx"""
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
    with patch('pygpt_net.core.tokens.tokens.Tokens.from_str', return_value=8):
        assert Tokens.from_ctx(item, 'chat', model) == 56


def test_get_config():
    """Test get_config"""
    model = "gpt-4-0613"
    assert Tokens.get_config(model) == ('gpt-4-0613', 3, 1)
