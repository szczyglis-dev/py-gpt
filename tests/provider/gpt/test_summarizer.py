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

from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window_conf
from pygpt_net.provider.gpt.summarizer import Summarizer
from pygpt_net.item.ctx import CtxItem


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


def test_summary_ctx(mock_window_conf):
    """
    Test prepare ctx name
    """
    model = ModelItem()
    summarizer = Summarizer(mock_window_conf)
    summarizer.window.core.models.from_defaults = MagicMock(return_value=model)
    summarizer.window.core.bridge.quick_call = MagicMock(return_value='test_response')
    summarizer.window.core.config.get.side_effect = mock_get
    summarizer.window.core.models.get_num_ctx = MagicMock(return_value=2048)
    summarizer.window.core.ctx.get_prompt_items = MagicMock(return_value=[])
    response = summarizer.summary_ctx(CtxItem())
    assert response == 'test_response'

