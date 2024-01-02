#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

import os

from unittest.mock import MagicMock

from tests.mocks import mock_window_conf
from pygpt_net.config import Config


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200


def test_get_user_path(mock_window_conf):
    """
    Test get user path
    """
    config = Config(mock_window_conf)
    config.path = 'test_path'
    assert config.get_user_path() == 'test_path'


def test_get_available_langs(mock_window_conf):
    """
    Test get available languages
    """
    config = Config(mock_window_conf)
    config.get_app_path = MagicMock(return_value='test_path')
    config.get_user_path = MagicMock(return_value='test_path')
    os.path.exists = MagicMock(return_value=True)
    os.listdir = MagicMock(return_value=['locale.en.ini', 'locale.de.ini', 'locale.fr.ini'])
    assert config.get_available_langs() == ['en', 'de', 'fr']

