#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.core.idx.context import Context


def test_get_messages(mock_window):
    """Test get messages"""
    item1 = CtxItem()
    item1.input = "test1"
    item1.output = "test2"
    item2 = CtxItem()
    item2.input = "test3"
    item2.output = "test4"
    items = [item1, item2]
    mock_window.core.ctx.get_prompt_items = MagicMock(return_value=items)
    mock_window.core.config.set('max_total_tokens', 100)
    mock_window.core.config.set('use_context', True)
    mock_window.core.models.get_num_ctx = MagicMock(return_value=100)
    mock_window.core.tokens.from_user = MagicMock(return_value=10)
    ctx = Context(mock_window)
    input_prompt = "test"
    system_prompt = "test"

    messages = ctx.get_messages(input_prompt, system_prompt)
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[0].content == "test1"
    assert messages[1].role == "assistant"
    assert messages[1].content == "test2"
    assert messages[2].role == "user"
    assert messages[2].content == "test3"
    assert messages[3].role == "assistant"
    assert messages[3].content == "test4"
