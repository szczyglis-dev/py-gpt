#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.07 21:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from tests.mocks import mock_window
from pygpt_net.controller import Theme


def test_update(mock_window):
    """Test update markdown"""
    theme = Theme(mock_window)
    theme.window.controller.ui.store_state = MagicMock()
    theme.window.controller.ui.restore_state = MagicMock()
    theme.window.core.config.get = MagicMock(return_value=True)
    theme.markdown.load = MagicMock()
    theme.markdown.set_default = MagicMock()
    theme.markdown.apply = MagicMock()
    theme.markdown.update(force=True)
    theme.window.controller.ui.store_state.assert_called()
    theme.markdown.load.assert_called()
    theme.markdown.set_default.assert_not_called()
    theme.markdown.apply.assert_called()
    theme.window.controller.ui.restore_state.assert_called()


def test_get_default(mock_window):
    """Test get default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    assert theme.markdown.get_default() is not None


def test_set_default(mock_window):
    """Test set default markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    theme.markdown.css['markdown'] = {}
    theme.markdown.set_default()
    assert theme.markdown.css['markdown'] is not None


def test_apply(mock_window):
    """Test apply markdown"""
    mock_window.core.config.data['theme'] = 'light'
    theme = Theme(mock_window)
    mock_window.ui.nodes = {'output': MagicMock()}
    mock_window.ui.nodes = {'output_plain': MagicMock()}
    mock_window.controller.chat.render.reload()
    theme.markdown.css['markdown'] = {}
    theme.markdown.apply()
    mock_window.controller.chat.render.reload.assert_called()


def test_load(mock_window):
    """Test load markdown"""
    mock_window.core.config.data['theme'] = 'light'
    with patch('os.path.exists') as os_path_exists, \
        patch('os.path.join') as os_path_join:
        os_path_exists.return_value=True
        os_path_join.return_value='test'
        theme = Theme(mock_window)

        with patch('builtins.open', mock_open(read_data='test')) as mock_file:
            theme.markdown.load()
            assert theme.markdown.css['markdown'] is not None
            assert theme.markdown.css['web'] is not None
