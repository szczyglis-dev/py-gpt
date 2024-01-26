#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.26 18:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.provider.gpt.image import Image


def test_generate(mock_window):
    """Test generate"""
    image = Image(mock_window)
    ctx = CtxItem()
    image.window.core.gpt.get_client = MagicMock()
    model = ModelItem()
    model.id = 'test'
    image.generate(
        ctx=ctx,
        prompt='test',
        model=model,
        num=1,
        inline=False,
    )
    image.window.threadpool.start.assert_called_once()
    image.window.core.gpt.get_client.assert_called_once()
