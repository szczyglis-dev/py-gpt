#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.12 14:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from tests.mocks import mock_window
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.gpt.image import Image


def test_generate(mock_window):
    """Test generate"""
    image = Image(mock_window)
    ctx = CtxItem()
    image.window.core.gpt.get_client = MagicMock()
    model = ModelItem()
    model.id = 'test'
    bridge_context = BridgeContext(
        ctx=ctx,
        prompt='test',
        model=model,
    )
    extra = {
        'num': 1,
        'inline': False,
    }
    image.generate(
        context=bridge_context,
        extra=extra,
    )
    image.window.core.gpt.get_client.assert_called_once()
