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

from tests.mocks import mock_window
from pygpt_net.core.info import Info


def test_init(mock_window):
    """Test init"""
    info = Info(mock_window)
    assert info.active['about'] is False
