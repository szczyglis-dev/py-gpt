#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from unittest.mock import patch

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_get_extra_css(mock_window):
    """Test get extra css"""
    mock_window.core.config.data['theme'] = 'dark_teal'
    theme = Theme(mock_window)
    with patch('os.path.exists') as os_path_exists, \
        patch('os.path.join') as os_path_join:
        os_path_exists.return_value=True
        os_path_join.return_value='test'
        assert theme.common.get_extra_css('dark_teal') == 'style.dark.css'


def test_translate(mock_window):
    name = 'dark_teal'
    theme = Theme(mock_window)
    mock_window.core.config.data['lang'] = 'en'
    assert theme.common.translate(name) == 'Dark: Teal'  # must have EN lang in config to pass!!!!!!!!


def test_get_themes_list(mock_window):
    theme = Theme(mock_window)
    assert type(theme.common.get_themes_list()) == list
