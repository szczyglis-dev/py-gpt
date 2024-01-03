#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 19:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.core.history import History


def test_install(mock_window):
    """Test install"""
    history = History(mock_window)
    history.provider = MagicMock()
    history.provider.install = MagicMock()
    history.install()
    history.provider.install.assert_called_once()


def test_append(mock_window):
    """Test append"""
    history = History(mock_window)
    history.provider = MagicMock()
    history.provider.append = MagicMock()
    ctx = CtxItem()
    mode = 'chat'
    history.append(ctx, mode)
    history.provider.append.assert_called_once()
