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
from pygpt_net.core.locale import Locale


def test_reload(mock_window):
    """Test reload"""
    config = MagicMock()
    locale = Locale(domain=None, config=config)
    locale.load = MagicMock()
    locale.reload()
    locale.load.assert_called_once()


def load(mock_window):
    """Test load"""
    config = MagicMock()
    locale = Locale(domain=None, config=config)
    locale.load = MagicMock()
    locale.load('en')
    locale.load.assert_called_once()


def test_get(mock_window):
    """Test get"""
    config = MagicMock()
    locale = Locale(domain=None, config=config)
    locale.data = {'locale': {'test': 'translated'}}
    locale.load = MagicMock()
    assert locale.get('test') == 'translated'
    locale.load.assert_not_called()  # already have data
