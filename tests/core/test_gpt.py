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
from pygpt_net.provider.gpt import Gpt


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
    response = gpt.quick_call('test_prompt', 'test_system_prompt')
    assert response == 'test_response'
