#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.core.idx.llm import Llm


def test_init(mock_window):
    """Test init"""
    mock_window.core.config.set("api_key", "test_api_key")
    llm = Llm(mock_window)
    llm.init()
    assert os.environ['OPENAI_API_KEY'] == "test_api_key"


def test_get(mock_window):
    """Test get"""
    model = ModelItem()
    provider = MagicMock()
    provider.init = MagicMock()
    provider.llama = MagicMock()
    mock_window.core.llm.llms = {
        "openai": provider
    }
    model.provider = "openai"
    llm = Llm(mock_window)
    llm.get(model)
    provider.init.assert_called_once()
    provider.llama.assert_called_once()
