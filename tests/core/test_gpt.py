#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 15:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.provider.gpt import Gpt
from tests.mocks import mock_window_conf

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


def test_quick_call(mock_window_conf):
    """
    Test quick call
    """
    client = MagicMock(return_value='test_response')
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = 'test_response'
    client.chat.completions.create.return_value = mock_response
    gpt = Gpt(mock_window_conf)
    gpt.get_client = MagicMock(return_value=client)
    gpt.build_chat_messages = MagicMock(return_value='test_messages')
    gpt.window.core.config.get.side_effect = mock_get
    bridge_context = BridgeContext(
        prompt='test_prompt',
        system_prompt='test_system_prompt',
    )
    response = gpt.quick_call(
        context=bridge_context,
    )
    assert response == 'test_response'
