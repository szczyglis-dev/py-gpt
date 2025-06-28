#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock
from tests.mocks import mock_window_conf

from pygpt_net.core.bridge.context import BridgeContext
# from pygpt_net.core.chain import Chain
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def test_call(mock_window_conf):
    """
    Test call
    
    ctx = CtxItem()
    ctx.input = 'test_input'
    ctx.input_name = 'User'
    ctx.output_name = 'AI'

    model = ModelItem()
    model.name = 'test'
    model.langchain = {
        'provider': 'test',
        'mode': ['chat', 'completion']
    }

    mock_window_conf.core.models.get.return_value = model
    chain = Chain(mock_window_conf)
    chain.chat = MagicMock()
    chain.chat.send.content = MagicMock()
    chain.completion.send = MagicMock()
    chain.chat.send.content.return_value = 'test_chat_response'
    chain.completion.send.return_value = 'test_completion_response'
    bridge_context = BridgeContext(
        ctx=ctx,
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        model=model,
    )
    extra = {}
    chain.call(
        context=bridge_context,
        extra=extra,
    )
    chain.chat.send.assert_called_once_with(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
        model=model,
        history=[],
        ai_name='AI',
        user_name='User',
        stream=False,
    )
    """
