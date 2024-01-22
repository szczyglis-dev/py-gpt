#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 13:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch, mock_open
from tests.mocks import mock_window
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.history.txt_file import TxtFileProvider


def test_install(mock_window):
    """Test install"""
    provider = TxtFileProvider(mock_window)
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value = True
        provider.install()
        os_path_exists.assert_called_once()


def test_append(mock_window):
    """Test append"""
    provider = TxtFileProvider(mock_window)
    mock_window.core.config.data['store_history_time'] = False
    ctx = CtxItem()
    ctx.input = "test"
    ctx.output = "test"
    ctx.input_timestamp = 0
    ctx.output_timestamp = 0
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value = True
        with patch('builtins.open', mock_open()) as mocked_file:
            mocked_file.return_value.write = MagicMock()
            provider.append(ctx, 'input')
            mocked_file.assert_called_once()


def test_truncate(mock_window):
    """Test truncate"""
    provider = TxtFileProvider(mock_window)
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value = False
        provider.truncate()
        os_path_exists.assert_called_once()
