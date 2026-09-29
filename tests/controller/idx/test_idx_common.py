#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 06:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.idx.common import Common


def test_setup(mock_window):
    """Setup is intentionally a no-op and keeps the controller usable."""
    common = Common(mock_window)

    result = common.setup()

    assert result is None
    assert common.window is mock_window
