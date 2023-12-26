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
from pygpt_net.core.gpt.summarizer import Summarizer
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


def test_summary_ctx(mock_window):
    """
    Test prepare ctx name
    """
    summarizer = Summarizer(mock_window)
    summarizer.window.core.gpt.quick_call = MagicMock(return_value='test_response')
    summarizer.window.core.config.get.side_effect = mock_get
    summarizer.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    summarizer.window.core.ctx.get_prompt_items = MagicMock(return_value=[])
    response = summarizer.summary_ctx(CtxItem())
    assert response == 'test_response'

