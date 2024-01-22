#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.05 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch, mock_open, Mock

from tests.mocks import mock_window
from pygpt_net.llm.Llama2 import Llama2LLM as Wrapper


def test_completion(mock_window):
    config = mock_window.core.config
    options = {}
    stream = False
    wrapper = Wrapper()
    wrapper.completion = MagicMock(return_value=Mock())
    wrapper.completion(config, options, stream)
    wrapper.completion.assert_called_once()


def test_chat(mock_window):
    config = mock_window.core.config
    options = {}
    stream = False
    wrapper = Wrapper()
    wrapper.chat = MagicMock(return_value=Mock())
    wrapper.chat(config, options, stream)
    wrapper.chat.assert_called_once()
    