#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.07 00:30:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.mocks import mock_window_conf

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.chain import Chain
from pygpt_net.core.types import MODE_CHAT
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


def test_call(mock_window_conf):
    """Chat sub-mode forwards bridge data and stores the returned content."""
    ctx = CtxItem()
    ctx.input_name = "User"
    ctx.output_name = "AI"

    model = ModelItem("test")
    model.langchain = {
        "provider": "test",
        "mode": [MODE_CHAT],
    }

    chain = Chain(mock_window_conf)
    response = SimpleNamespace(content="test_chat_response")
    chain.chat.send = MagicMock(return_value=response)
    chain.chat.get_used_tokens = MagicMock(return_value=17)

    history = [CtxItem()]
    bridge_context = BridgeContext(
        ctx=ctx,
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
        history=history,
        stream=False,
    )

    result = chain.call(context=bridge_context, extra={"unused": True})

    assert result is True
    assert ctx.output == "test_chat_response"
    assert ctx.output_name == "AI"
    chain.chat.send.assert_called_once_with(
        prompt="test_prompt",
        system_prompt="test_system_prompt",
        model=model,
        history=history,
        stream=False,
        ai_name="AI",
        user_name="User",
    )
    chain.chat.get_used_tokens.assert_called_once_with()
